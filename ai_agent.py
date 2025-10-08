"""
ai_agent.py - OpenAI integration for content generation
Uses gpt-4o-mini for text (cost-effective), gpt-image-1 for images.
Implements aggressive caching to minimize API costs.
All prompts optimized for brevity and quality output.
"""
import os
import base64
import json
import hashlib
from typing import Any, Optional
from tenacity import retry, stop_after_attempt, wait_exponential, retry_if_exception_type
from openai import OpenAI, APIError, RateLimitError
from config import CFG
from cache import get_cached, set_cached
from db import log_event

# Initialize OpenAI client
client = OpenAI(api_key=CFG["OPENAI_API_KEY"])

# Cost estimates (as of 2024, update periodically)
COSTS = {
    "gpt-4o-mini": {"input": 0.00015 / 1000, "output": 0.0006 / 1000},  # per token
    "gpt-image-1": 0.020,  # per image (1024x1024)
}


def _hash_short(d: dict[str, Any]) -> str:
    """Generate short hash for logging."""
    return hashlib.sha256(json.dumps(d, sort_keys=True).encode()).hexdigest()[:12]


@retry(
    stop=stop_after_attempt(3),
    wait=wait_exponential(multiplier=1, min=2, max=10),
    retry=retry_if_exception_type((APIError, RateLimitError)),
)
def generate_text(
    topic: str,
    brand_bullets: list[str],
    style: str,
    variants: int = 3
) -> dict[str, Any]:
    """
    Generate social media post variants using OpenAI.
    
    Args:
        topic: Main topic/headline
        brand_bullets: Brand voice/context bullets
        style: Writing style (e.g., 'educational', 'funny')
        variants: Number of variants to generate
    
    Returns:
        {"variants": [{"title": str, "body": str}, ...]}
    """
    payload = {"topic": topic, "brand": brand_bullets, "style": style, "v": variants}
    
    # Check cache first
    cached, meta = get_cached("text_v1", payload)
    if cached:
        log_event("ai_agent", "INFO", "Using cached text generation", {"hash": _hash_short(payload)})
        return json.loads(cached)
    
    # Build prompt (keep it short to minimize token cost)
    system_prompt = (
        "You are a social content generator. Return concise, high-signal posts with:\n"
        "- Strong hook in first line\n"
        "- 1 clear CTA\n"
        "- 3-5 hashtags (lowercase)\n"
        "- No fluff, direct value\n"
        "Output JSON: {\"variants\":[{\"title\": str, \"body\": str}]}"
    )
    
    user_prompt = (
        f"Topic: {topic}\n\n"
        f"Brand voice:\n- {chr(10).join(brand_bullets)}\n\n"
        f"Style: {style}\n"
        f"Generate {variants} variants optimized for LinkedIn & Facebook."
    )
    
    log_event("ai_agent", "INFO", "Calling OpenAI text generation", {"topic": topic[:50]})
    
    try:
        response = client.chat.completions.create(
            model="gpt-4o-mini",
            temperature=0.4,
            max_tokens=1500,  # Control output length
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt}
            ],
            response_format={"type": "json_object"}
        )
        
        output = response.choices[0].message.content
        tokens_used = response.usage.total_tokens if response.usage else 0
        
        # Calculate cost
        cost_usd = (
            response.usage.prompt_tokens * COSTS["gpt-4o-mini"]["input"] +
            response.usage.completion_tokens * COSTS["gpt-4o-mini"]["output"]
        ) if response.usage else 0
        
        # Cache the result
        metadata = {"tokens": tokens_used, "cost_usd": cost_usd}
        set_cached("text_v1", payload, output, metadata)
        
        log_event("ai_agent", "INFO", f"Generated {variants} text variants", metadata)
        
        return json.loads(output)
    
    except Exception as e:
        log_event("ai_agent", "ERROR", f"Text generation failed: {e}", {"topic": topic})
        raise


@retry(
    stop=stop_after_attempt(3),
    wait=wait_exponential(multiplier=1, min=2, max=10),
    retry=retry_if_exception_type((APIError, RateLimitError)),
)
def generate_image(prompt: str, size: str = "1024x1024") -> bytes:
    """
    Generate image using DALL-E.
    
    Args:
        prompt: Image description
        size: Image dimensions (1024x1024, 1792x1024, 1024x1792)
    
    Returns:
        Raw PNG image bytes
    """
    payload = {"img_prompt": prompt, "size": size}
    
    # Check cache
    cached, meta = get_cached("img_v1", payload)
    if cached and meta.get("path") and os.path.exists(meta["path"]):
        log_event("ai_agent", "INFO", "Using cached image", {"path": meta["path"]})
        with open(meta["path"], "rb") as f:
            return f.read()
    
    log_event("ai_agent", "INFO", "Calling OpenAI image generation", {"prompt": prompt[:50]})
    
    try:
        response = client.images.generate(
            model="dall-e-3",  # Updated model name
            prompt=prompt,
            size=size,
            quality="standard",  # 'standard' is cheaper than 'hd'
            n=1,
            response_format="b64_json"
        )
        
        # Decode base64 image
        b64_data = response.data[0].b64_json
        raw_bytes = base64.b64decode(b64_data)
        
        # Save to media dir for caching
        os.makedirs(CFG["MEDIA_DIR"], exist_ok=True)
        cache_path = os.path.join(CFG["MEDIA_DIR"], f"cached_{_hash_short(payload)}.png")
        with open(cache_path, "wb") as f:
            f.write(raw_bytes)
        
        # Cache reference
        metadata = {"path": cache_path, "cost_usd": COSTS["gpt-image-1"]}
        set_cached("img_v1", payload, "OK", metadata)
        
        log_event("ai_agent", "INFO", "Generated image", {"path": cache_path, "cost_usd": COSTS["gpt-image-1"]})
        
        return raw_bytes
    
    except Exception as e:
        log_event("ai_agent", "ERROR", f"Image generation failed: {e}", {"prompt": prompt})
        raise


def bmad_supervisor(topics: list[str], brand_bullets: list[str]) -> dict[str, str]:
    """
    BMAD Supervisor: strategic content planning.
    Analyzes topics and brand, returns best content plan.
    
    Args:
        topics: List of trending topics
        brand_bullets: Brand voice/context
    
    Returns:
        {
            "title": str,
            "body_style": str,
            "image_prompt": str,
            "reasoning": str,
            "selected_topic": str
        }
    """
    payload = {"topics": topics, "brand": brand_bullets}
    
    # Check cache
    cached, meta = get_cached("bmad_v1", payload)
    if cached:
        log_event("ai_agent", "INFO", "Using cached BMAD plan")
        return json.loads(cached)
    
    system_prompt = (
        "You are the BMAD Supervisor (Architect/Strategist/Developer/Debugger/Manager). "
        "Analyze topics and brand context, then select the BEST single content opportunity. "
        "Consider: relevance, engagement potential, brand fit, timeliness. "
        "Output JSON: {\"title\": str, \"body_style\": str, \"image_prompt\": str, "
        "\"reasoning\": str, \"selected_topic\": str}"
    )
    
    user_prompt = (
        f"Trending Topics:\n{chr(10).join(f'- {t}' for t in topics[:10])}\n\n"
        f"Brand Context:\n{chr(10).join(f'- {b}' for b in brand_bullets)}\n\n"
        "Select best topic and create content plan. Keep body under 900 chars."
    )
    
    log_event("ai_agent", "INFO", "Calling BMAD Supervisor", {"topics_count": len(topics)})
    
    try:
        response = client.chat.completions.create(
            model="gpt-4o-mini",
            temperature=0.3,  # Lower temperature for strategic decisions
            max_tokens=800,
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt}
            ],
            response_format={"type": "json_object"}
        )
        
        output = response.choices[0].message.content
        
        # Calculate cost
        cost_usd = (
            response.usage.prompt_tokens * COSTS["gpt-4o-mini"]["input"] +
            response.usage.completion_tokens * COSTS["gpt-4o-mini"]["output"]
        ) if response.usage else 0
        
        metadata = {"cost_usd": cost_usd, "tokens": response.usage.total_tokens if response.usage else 0}
        set_cached("bmad_v1", payload, output, metadata)
        
        log_event("ai_agent", "INFO", "BMAD plan created", metadata)
        
        return json.loads(output)
    
    except Exception as e:
        log_event("ai_agent", "ERROR", f"BMAD planning failed: {e}")
        raise

