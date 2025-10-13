"""
social_poster.py - Social media platform publishing with retries.
Handles Facebook Pages and LinkedIn (personal/org) posting.
Implements exponential backoff for rate limits and transient errors.
"""
import httpx
import time
from typing import Optional
from config import CFG
from db import log_event

def _retry_request(func, max_retries=3, initial_delay=2.0):
    """
    Retry wrapper for HTTP requests with exponential backoff.
    """
    for attempt in range(max_retries):
        try:
            return func()
        except httpx.HTTPStatusError as e:
            # Don't retry on 4xx client errors (except 429 rate limit)
            if 400 <= e.response.status_code < 500 and e.response.status_code != 429:
                raise
            if attempt == max_retries - 1:
                raise
            delay = initial_delay * (2 ** attempt)
            log_event("social_poster", "warning", 
                     f"HTTP error {e.response.status_code}, retry {attempt+1}/{max_retries} after {delay}s",
                     {"status": e.response.status_code, "body": e.response.text[:200]})
            time.sleep(delay)
        except (httpx.RequestError, httpx.TimeoutException) as e:
            if attempt == max_retries - 1:
                raise
            delay = initial_delay * (2 ** attempt)
            log_event("social_poster", "warning", 
                     f"Request error, retry {attempt+1}/{max_retries} after {delay}s",
                     {"error": str(e)})
            time.sleep(delay)
    raise RuntimeError(f"Max retries ({max_retries}) exceeded")

# ---------- Facebook ----------
def post_facebook(message: str, image_path: Optional[str] = None) -> str:
    """
    Post to Facebook Page using Graph API.
    Args:
        message: Post text content
        image_path: Optional path to image file
    Returns:
        Permalink URL of published post
    """
    page_id = CFG["FB_PAGE_ID"]
    token = CFG["FB_PAGE_ACCESS_TOKEN"]
    
    if not page_id or not token:
        raise ValueError("FB_PAGE_ID and FB_PAGE_ACCESS_TOKEN required")
    
    base = f"https://graph.facebook.com/v21.0/{page_id}"
    
    def _post():
        with httpx.Client(timeout=30) as client:
            if image_path:
                # Upload photo with caption
                with open(image_path, "rb") as f:
                    files = {"source": f}
                    data = {"caption": message, "access_token": token}
                    r = client.post(f"{base}/photos", data=data, files=files)
            else:
                # Text-only post
                r = client.post(f"{base}/feed", data={"message": message, "access_token": token})
            
            r.raise_for_status()
            j = r.json()
            
            # Fetch permalink
            post_id = j.get("post_id") or j.get("id")
            if not post_id:
                return ""
            
            pr = client.get(
                f"https://graph.facebook.com/v21.0/{post_id}",
                params={"fields": "permalink_url", "access_token": token}
            )
            pr.raise_for_status()
            return pr.json().get("permalink_url", "")
    
    result = _retry_request(_post)
    log_event("social_poster", "info", "Facebook post published", {"has_image": bool(image_path)})
    return result

# ---------- LinkedIn ----------
def post_linkedin(message: str, image_path: Optional[str] = None) -> str:
    """
    Post to LinkedIn using intelligent hybrid strategy.
    Tries Official API first (if configured), falls back to Selenium.
    
    Args:
        message: Post text content
        image_path: Optional path to image file
    Returns:
        Result message (timestamp or post ID)
    
    Note:
        Uses linkedin_poster.py which automatically selects best method:
        1. Official API (if configured)
        2. Selenium automation (always works)
        3. Error notification if both fail
    """
    try:
        from linkedin_poster import post_to_linkedin as unified_post
        
        log_event("social_poster", "info", "Using LinkedIn unified posting strategy", 
                 {"has_image": bool(image_path)})
        
        success, result = unified_post(message, image_path)
        
        if success:
            log_event("social_poster", "info", "LinkedIn post published", 
                     {"result": result, "has_image": bool(image_path)})
            return result
        else:
            log_event("social_poster", "error", f"LinkedIn posting failed: {result}")
            raise RuntimeError(f"LinkedIn posting failed: {result}")
            
    except ImportError:
        # Fallback to old method if linkedin_poster not available
        log_event("social_poster", "warning", "linkedin_poster not available, using legacy method")
        
        # Try Selenium directly
        try:
            from linkedin_selenium import post_to_linkedin as selenium_post
            result = selenium_post(message, image_path, headless=True)
            if result:
                return result
        except:
            pass
        
        raise RuntimeError("No LinkedIn posting method available")
