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

def generate_text(topic: str, brand_bullets: list[str], style: str, variants: int = 3) -> dict:
    """
    Generate multiple text variants for a topic.
    Args:
        topic: Main topic/theme
        brand_bullets: List of brand voice guidelines
        style: Writing style (e.g. 'professional', 'casual')
        variants: Number of variants to generate
    Returns:
        {"variants": [{"title": str, "body": str}, ...]}
    """
    # Check budget before expensive call
    budget = check_budget_limit("text_generation")
    if not budget["ok"]:
        log_event("ai_agent", "error", f"Budget limit exceeded: {budget['reason']}")
        raise RuntimeError(f"Budget limit exceeded: {budget['reason']}")
    
    payload = {"topic": topic, "brand": brand_bullets, "style": style, "v": variants}
    cached, meta = get_cached("text_v1", payload)
    if cached:
        log_event("ai_agent", "info", "Text generation cache hit", {"topic": topic[:50]})
        return json.loads(cached)

    sys = (
        "You are a social content generator. Return concise, high-signal posts with a strong hook, "
        "1 CTA, 3-5 hashtags (lowercase), and no fluff. Output JSON: {\"variants\":[{\"title\": \"...\", \"body\": \"...\"}]}."
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
        log_openai_cost("text_generation", "gpt-4o-mini", usage_dict, {"topic": topic[:50]})
    
    set_cached("text_v1", payload, out, {"tokens": rsp.usage.total_tokens if rsp.usage else None})
    log_event("ai_agent", "info", "Text generated", {"topic": topic[:50], "variants": variants})
    return json.loads(out)

def generate_image(prompt: str, size: str = "1024x1024", save_path: Optional[str] = None) -> bytes:
    """
    Generate image using OpenAI image API.
    Args:
        prompt: Image generation prompt
        size: Image size (1024x1024, 1792x1024, etc.)
        save_path: Optional path to save image
    Returns:
        Image bytes
    """
    # Check budget
    budget = check_budget_limit("image_generation")
    if not budget["ok"]:
        log_event("ai_agent", "error", f"Budget limit exceeded: {budget['reason']}")
        raise RuntimeError(f"Budget limit exceeded: {budget['reason']}")
    
    payload = {"img_prompt": prompt, "size": size}
    cached, meta = get_cached("img_v1", payload)
    if cached and meta.get("path") and os.path.exists(meta["path"]):
        log_event("ai_agent", "info", "Image generation cache hit", {"prompt": prompt[:50]})
        with open(meta["path"], "rb") as f:
            return f.read()

    def _call():
        return client.images.generate(model="dall-e-3", prompt=prompt, size=size, response_format="b64_json")
    
    img = _retry_with_backoff(_call)
    b64 = img.data[0].b64_json
    raw = base64.b64decode(b64)
    
    # Log cost (flat rate per image)
    cost = calculate_image_cost("dall-e-3", size)
    from db import record_cost
    record_cost("image_generation", "dall-e-3", 0, cost, {"prompt": prompt[:50], "size": size})
    
    # Save to cache
    cache_path = save_path or os.path.join(CFG["MEDIA_DIR"], f"cached_{hashlib.md5(prompt.encode()).hexdigest()[:12]}.png")
    os.makedirs(os.path.dirname(cache_path), exist_ok=True)
    with open(cache_path, "wb") as f:
        f.write(raw)
    
    set_cached("img_v1", payload, "OK", {"path": cache_path})
    log_event("ai_agent", "info", "Image generated", {"prompt": prompt[:50], "size": size})
    return raw

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
        "Pick the best single content plan for LinkedIn & Facebook, return JSON: "
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
