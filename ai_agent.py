"""
ai_agent.py - OpenAI API integration for content generation.
Implements BMAD Supervisor pattern: batch variants, cache aggressively, short prompts.
Handles text (gpt-4o-mini) and image (gpt-image-1) generation with retries.
"""
import os
import base64
import time
import json
import hashlib
from typing import Optional
from openai import OpenAI, APIError, RateLimitError, APIConnectionError
from config import CFG
from cache import get_cached, set_cached
from cost import log_openai_cost, calculate_image_cost, check_budget_limit
from db import log_event

client = OpenAI(api_key=CFG["OPENAI_API_KEY"])

def _retry_with_backoff(func, max_retries=3, initial_delay=1.0):
    """
    Exponential backoff retry wrapper for API calls.
    """
    for attempt in range(max_retries):
        try:
            return func()
        except RateLimitError as e:
            if attempt == max_retries - 1:
                raise
            delay = initial_delay * (2 ** attempt)
            log_event("ai_agent", "warning", f"Rate limit hit, retry {attempt+1}/{max_retries} after {delay}s", {"error": str(e)})
            time.sleep(delay)
        except (APIConnectionError, APIError) as e:
            if attempt == max_retries - 1:
                raise
            delay = initial_delay * (2 ** attempt)
            log_event("ai_agent", "warning", f"API error, retry {attempt+1}/{max_retries} after {delay}s", {"error": str(e)})
            time.sleep(delay)
    raise RuntimeError(f"Max retries ({max_retries}) exceeded")

def generate_text(topic: str, brand_bullets: list[str], style: str, variants: int = 3, 
                  persona_prompt: Optional[str] = None, persona_id: Optional[str] = None) -> dict:
    """
    Generate multiple text variants for a topic.
    Args:
        topic: Main topic/theme
        brand_bullets: List of brand voice guidelines
        style: Writing style (e.g. 'professional', 'casual')
        variants: Number of variants to generate
        persona_prompt: Optional custom persona prompt (overrides default)
        persona_id: Optional persona identifier for caching
    Returns:
        {"variants": [{"title": str, "body": str}, ...]}
    """
    # Check budget before expensive call
    budget = check_budget_limit("text_generation")
    if not budget["ok"]:
        log_event("ai_agent", "error", f"Budget limit exceeded: {budget['reason']}")
        raise RuntimeError(f"Budget limit exceeded: {budget['reason']}")
    
    payload = {"topic": topic, "brand": brand_bullets, "style": style, "v": variants, 
               "persona": persona_id or "default"}
    cached, meta = get_cached("text_v2", payload)  # v2 to include persona
    if cached:
        log_event("ai_agent", "info", "Text generation cache hit", 
                 {"topic": topic[:50], "persona": persona_id})
        return json.loads(cached)

    # Use persona prompt if provided, otherwise use default
    # IMPORTANT: Must include "json" in prompt when using response_format
    if persona_prompt:
        sys = persona_prompt + "\n\nYou must return your response as valid JSON with this exact structure: {\"variants\":[{\"title\": \"...\", \"body\": \"...\"}]}"
    else:
        sys = (
            "You are a social content generator. Return concise, high-signal posts with a strong hook, "
            "1 CTA, 3-5 hashtags (lowercase), and no fluff. "
            "You must return your response as valid JSON with this exact structure: {\"variants\":[{\"title\": \"...\", \"body\": \"...\"}]}."
        )
    
    user = f"Topic: {topic}\nBrand:\n- " + "\n- ".join(brand_bullets) + f"\nStyle: {style}\nVariants: {variants}"

    def _call():
        return client.chat.completions.create(
            model="gpt-4o-mini",
            temperature=0.4,
            messages=[{"role": "system", "content": sys}, {"role": "user", "content": user}],
            response_format={"type": "json_object"}
        )
    
    rsp = _retry_with_backoff(_call)
    out = rsp.choices[0].message.content
    
    # Log cost
    if rsp.usage:
        usage_dict = {
            "prompt_tokens": rsp.usage.prompt_tokens,
            "completion_tokens": rsp.usage.completion_tokens,
            "total_tokens": rsp.usage.total_tokens
        }
        log_openai_cost("text_generation", "gpt-4o-mini", usage_dict, 
                       {"topic": topic[:50], "persona": persona_id})
    
    set_cached("text_v2", payload, out, {"tokens": rsp.usage.total_tokens if rsp.usage else None})
    log_event("ai_agent", "info", "Text generated", 
             {"topic": topic[:50], "variants": variants, "persona": persona_id})
    return json.loads(out)

def generate_image(prompt: str, size: str = "1024x1024", save_path: Optional[str] = None, 
                   prefer_canva: bool = True) -> Optional[bytes]:
    """
    Generate brand-safe image using Canva API (primary) or DALL-E (fallback).
    Automatically retries if text is detected in generated image.
    
    Args:
        prompt: Image generation prompt
        size: Image size (1024x1024, 1792x1024, etc.) - used for DALL-E
        save_path: Optional path to save image
        prefer_canva: If True, try Canva first before falling back to DALL-E
    Returns:
        Image bytes or None if all retries failed
    """
    from image_utils import (load_image_style_config, build_brand_safe_prompt, 
                             detect_text_in_image, log_image_audit)
    from canva_client import generate_canva_image
    
    # Check budget
    budget = check_budget_limit("image_generation")
    if not budget["ok"]:
        log_event("ai_agent", "error", f"Budget limit exceeded: {budget['reason']}")
        raise RuntimeError(f"Budget limit exceeded: {budget['reason']}")
    
    # Load brand-safe style config
    style_config = load_image_style_config()
    max_retries = style_config.get("retries", 3)
    
    # Try Canva first if enabled and preferred
    if prefer_canva and CFG.get("USE_CANVA", False):
        log_event("ai_agent", "info", "Attempting Canva image generation", {"prompt": prompt[:50]})
        
        canva_data, canva_source = generate_canva_image(prompt, save_path)
        
        if canva_data and canva_source == "canva":
            log_event("ai_agent", "info", "Canva image generated successfully", 
                     {"prompt": prompt[:50], "size_kb": len(canva_data) / 1024})
            return canva_data
        elif canva_source == "disabled":
            log_event("ai_agent", "info", "Canva disabled, using DALL-E")
        else:
            log_event("ai_agent", "warning", f"Canva generation failed ({canva_source}), falling back to DALL-E")
    
    # DALL-E Fallback: Enhance prompt with brand-safe filters
    log_event("ai_agent", "info", "Using DALL-E for image generation")
    enhanced_prompt = build_brand_safe_prompt(prompt, style_config)
    log_event("ai_agent", "info", "Enhanced image prompt with brand filters", 
             {"original": prompt[:50], "enhanced": enhanced_prompt[:100]})
    
    payload = {"img_prompt": enhanced_prompt, "size": size}
    cached, meta = get_cached("img_v2", payload)  # v2 for brand-safe images
    if cached and meta.get("path") and os.path.exists(meta["path"]):
        log_event("ai_agent", "info", "Image generation cache hit (DALL-E)", {"prompt": enhanced_prompt[:50]})
        with open(meta["path"], "rb") as f:
            return f.read()

    # Attempt DALL-E image generation with text detection retry
    for attempt in range(1, max_retries + 1):
        try:
            def _call():
                return client.images.generate(model="dall-e-3", prompt=enhanced_prompt, 
                                            size=size, response_format="b64_json")
            
            img = _retry_with_backoff(_call)
            b64 = img.data[0].b64_json
            raw = base64.b64decode(b64)
            
            # Log cost (flat rate per image)
            cost = calculate_image_cost("dall-e-3", size)
            from db import record_cost
            record_cost("image_generation", "dall-e-3", 0, cost, 
                       {"prompt": enhanced_prompt[:50], "size": size, "attempt": attempt})
            
            # Save temporary file for text detection
            temp_path = save_path or os.path.join(CFG["MEDIA_DIR"], 
                                                  f"temp_{hashlib.md5(enhanced_prompt.encode()).hexdigest()[:12]}_attempt{attempt}.png")
            os.makedirs(os.path.dirname(temp_path), exist_ok=True)
            with open(temp_path, "wb") as f:
                f.write(raw)
            
            # Detect text in image
            has_text, text_count = detect_text_in_image(temp_path)
            
            if not has_text:
                # Success - no text detected
                log_image_audit(temp_path, attempt, False, 0, "kept")
                
                # Rename to final path if needed
                if save_path and temp_path != save_path:
                    os.rename(temp_path, save_path)
                    final_path = save_path
                else:
                    final_path = temp_path
                
                set_cached("img_v2", payload, "OK", {"path": final_path})
                log_event("ai_agent", "info", 
                         f"Brand-safe image generated (attempt {attempt}/{max_retries})", 
                         {"prompt": enhanced_prompt[:50], "size": size})
                return raw
            else:
                # Text detected - log and retry
                action = "regenerated" if attempt < max_retries else "failed"
                log_image_audit(temp_path, attempt, True, text_count, action)
                
                log_event("ai_agent", "warning", 
                         f"Text detected in image (attempt {attempt}/{max_retries}), regenerating...",
                         {"text_count": text_count, "path": temp_path})
                
                # Delete failed attempt
                if os.path.exists(temp_path):
                    os.remove(temp_path)
                
                if attempt == max_retries:
                    log_event("ai_agent", "error", 
                             "Max image generation retries exceeded, all contained text",
                             {"prompt": enhanced_prompt[:50]})
                    return None  # Failed after all retries
                    
        except Exception as e:
            log_event("ai_agent", "error", 
                     f"Image generation attempt {attempt} failed: {str(e)}")
            if attempt == max_retries:
                return None
    
    return None  # Should not reach here

def bmad_supervisor(topics: list[str], brand_bullets: list[str]) -> dict:
    """
    BMAD Supervisor: Architect/Strategist/Developer/Debugger/Manager roles.
    Selects best content strategy from discovered topics.
    
    Args:
        topics: List of discovered topic strings
        brand_bullets: Brand voice guidelines
    Returns:
        {"title": str, "body_style": str, "image_prompt": str, "reasoning": str}
    """
    payload = {"topics": topics[:10], "brand": brand_bullets}  # Cache top 10 topics
    cached, meta = get_cached("supervisor_v1", payload)
    if cached:
        log_event("ai_agent", "info", "Supervisor cache hit")
        return json.loads(cached)
    
    sys = (
        "You are the BMAD Supervisor (Architect/Strategist/Developer/Debugger/Manager). "
        "Pick the best single content plan for LinkedIn & Facebook. "
        "You must return your response as valid JSON with this exact structure: "
        "{\"title\": \"...\", \"body_style\": \"...\", \"image_prompt\": \"...\", \"reasoning\": \"...\"}. "
        "Keep body_style description under 100 chars. Image prompt should be vivid, safe, professional."
    )
    user = "Topics:\n- " + "\n- ".join(topics[:10]) + "\n\nBrand:\n- " + "\n- ".join(brand_bullets)

    def _call():
        return client.chat.completions.create(
            model="gpt-4o-mini",
            temperature=0.3,
            messages=[{"role": "system", "content": sys}, {"role": "user", "content": user}],
            response_format={"type": "json_object"}
        )
    
    rsp = _retry_with_backoff(_call)
    out = rsp.choices[0].message.content

    # Log cost
    if rsp.usage:
        usage_dict = {
            "prompt_tokens": rsp.usage.prompt_tokens,
            "completion_tokens": rsp.usage.completion_tokens,
            "total_tokens": rsp.usage.total_tokens
        }
        log_openai_cost("supervisor", "gpt-4o-mini", usage_dict)
    
    set_cached("supervisor_v1", payload, out, {"tokens": rsp.usage.total_tokens if rsp.usage else None})
    log_event("ai_agent", "info", "Supervisor decision made", {"topics_count": len(topics)})
    return json.loads(out)
