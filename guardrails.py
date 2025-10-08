"""
guardrails.py - Content validation and platform-specific constraints.
Enforces character limits, link policies, and basic quality checks.
Prevents posts from being rejected by social platforms.
"""
import re

# Platform limits (conservative to avoid truncation)
PLATFORM_LIMITS = {
    "linkedin": {"max_chars": 3000, "recommended": 1200, "max_links": 1},
    "facebook": {"max_chars": 63206, "recommended": 2000, "max_links": 1},
}

def enforce_platform_rules(text: str, platform: str) -> str:
    """
    Apply platform-specific formatting and constraints.
    Args:
        text: Post body text
        platform: 'linkedin' or 'facebook'
    Returns:
        Cleaned text within platform limits
    """
    limits = PLATFORM_LIMITS.get(platform, {"max_chars": 2000, "max_links": 1})
    t = text.strip()
    
    # Enforce recommended length
    max_len = limits["recommended"]
    if len(t) > max_len:
        t = t[:max_len-3] + "..."
    
    # Enforce link limit (keep first N links)
    max_links = limits["max_links"]
    link_pattern = r'https?://[^\s]+'
    links = re.findall(link_pattern, t)
    if len(links) > max_links:
        # Remove excess links
        for link in links[max_links:]:
            t = t.replace(link, "", 1)
    
    return t.strip()

def validate_post_content(title: str, body: str) -> list[str]:
    """
    Basic content validation.
    Returns list of validation errors (empty if valid).
    """
    errors = []
    if not body or len(body.strip()) < 10:
        errors.append("Post body too short (min 10 chars)")
    if title and len(title) > 200:
        errors.append("Title too long (max 200 chars)")
    if body and len(body) > 5000:
        errors.append("Body too long (max 5000 chars)")
    # TODO: Add profanity filter, spam detection, etc.
    return errors
