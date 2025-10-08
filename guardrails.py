"""
guardrails.py - Content validation and platform-specific rules
Enforces character limits, link policies, and platform constraints.
Prevents API errors and ensures professional, compliant content.
"""
import re
from typing import Optional


# Platform constraints (conservative for safety)
PLATFORM_LIMITS = {
    "linkedin": {
        "max_length": 1300,  # LinkedIn recommends 1200-1300
        "max_links": 1,
        "emoji_ok": True,
    },
    "facebook": {
        "max_length": 2000,  # Facebook allows more but shorter is better
        "max_links": 2,
        "emoji_ok": True,
    },
}


def enforce_platform_rules(text: str, platform: str) -> str:
    """
    Apply platform-specific content rules.
    
    Args:
        text: Post body text
        platform: 'linkedin' or 'facebook'
    
    Returns:
        Cleaned, compliant text
    """
    limits = PLATFORM_LIMITS.get(platform.lower(), PLATFORM_LIMITS["facebook"])
    
    # Normalize whitespace
    text = text.strip()
    text = re.sub(r'\s+', ' ', text)  # Collapse multiple spaces
    
    # Enforce length limit
    max_len = limits["max_length"]
    if len(text) > max_len:
        text = text[:max_len - 3] + "..."
    
    # Limit number of links
    max_links = limits["max_links"]
    links = re.findall(r'https?://[^\s]+', text)
    if len(links) > max_links:
        # Keep only first N links
        for link in links[max_links:]:
            text = text.replace(link, "", 1)
    
    return text.strip()


def validate_post_content(title: str, body: str, platform: str) -> list[str]:
    """
    Validate post content before publishing.
    
    Returns:
        List of error messages (empty if valid)
    """
    errors = []
    
    if not body or len(body.strip()) < 20:
        errors.append("Body too short (minimum 20 characters)")
    
    if len(body) > 3000:
        errors.append("Body exceeds maximum length (3000 characters)")
    
    # Check for suspicious patterns
    if body.count('#') > 10:
        errors.append("Too many hashtags (maximum 10)")
    
    urls = re.findall(r'https?://[^\s]+', body)
    if len(urls) > 3:
        errors.append("Too many URLs (maximum 3)")
    
    # Platform-specific checks
    if platform == "linkedin":
        if len(body) > 1300:
            errors.append("LinkedIn body exceeds recommended 1300 characters")
    elif platform == "facebook":
        if len(body) > 2000:
            errors.append("Facebook body exceeds 2000 characters")
    
    return errors


def sanitize_hashtags(text: str, max_hashtags: int = 7) -> str:
    """
    Clean up hashtags: lowercase, limit count, remove duplicates.
    
    Args:
        text: Text containing hashtags
        max_hashtags: Maximum number of hashtags to keep
    
    Returns:
        Text with cleaned hashtags
    """
    # Find all hashtags
    hashtags = re.findall(r'#\w+', text)
    
    # Remove hashtags from text
    text_without_tags = re.sub(r'#\w+', '', text).strip()
    
    # Clean and deduplicate
    seen = set()
    clean_tags = []
    for tag in hashtags:
        tag_lower = tag.lower()
        if tag_lower not in seen and len(clean_tags) < max_hashtags:
            clean_tags.append(tag_lower)
            seen.add(tag_lower)
    
    # Reconstruct
    if clean_tags:
        return f"{text_without_tags}\n\n{' '.join(clean_tags)}"
    return text_without_tags


def strip_emojis(text: str) -> str:
    """Remove emojis if needed for conservative audiences."""
    # Basic emoji removal (Unicode ranges)
    emoji_pattern = re.compile(
        "["
        "\U0001F600-\U0001F64F"  # emoticons
        "\U0001F300-\U0001F5FF"  # symbols & pictographs
        "\U0001F680-\U0001F6FF"  # transport & map symbols
        "\U0001F1E0-\U0001F1FF"  # flags
        "\U00002702-\U000027B0"
        "\U000024C2-\U0001F251"
        "]+", flags=re.UNICODE
    )
    return emoji_pattern.sub('', text)

