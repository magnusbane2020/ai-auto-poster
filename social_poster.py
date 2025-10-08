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
    Post to LinkedIn using UGC API (works for both personal and org accounts).
    Args:
        message: Post text content
        image_path: Optional path to image file
    Returns:
        Empty string (LinkedIn API v2 doesn't return immediate permalink)
    """
    token = CFG["LINKEDIN_ACCESS_TOKEN"]
    owner = CFG["LINKEDIN_ORG_URN"] or CFG["LINKEDIN_PERSON_URN"]
    
    if not token:
        raise ValueError("LINKEDIN_ACCESS_TOKEN required")
    if not owner:
        raise ValueError("Set LINKEDIN_PERSON_URN or LINKEDIN_ORG_URN")
    
    headers = {
        "Authorization": f"Bearer {token}",
        "X-Restli-Protocol-Version": "2.0.0",
        "Content-Type": "application/json"
    }

    def _post():
        with httpx.Client(timeout=45) as client:
            if image_path:
                # Step 1: Register upload
                init_resp = client.post(
                    "https://api.linkedin.com/v2/assets?action=registerUpload",
                    headers=headers,
                    json={
                        "registerUploadRequest": {
                            "recipes": ["urn:li:digitalmediaRecipe:feedshare-image"],
                            "owner": owner,
                            "serviceRelationships": [
                                {"relationshipType": "OWNER", "identifier": "urn:li:userGeneratedContent"}
                            ]
                        }
                    }
                )
                init_resp.raise_for_status()
                init_data = init_resp.json()
                
                upload_url = init_data["value"]["uploadMechanism"]["com.linkedin.digitalmedia.uploading.MediaUploadHttpRequest"]["uploadUrl"]
                asset = init_data["value"]["asset"]
                
                # Step 2: Upload binary image
                with open(image_path, "rb") as f:
                    upload_resp = client.put(
                        upload_url,
                        headers={"Authorization": f"Bearer {token}"},
                        content=f.read()
                    )
                    upload_resp.raise_for_status()
                
                # Step 3: Create post with image
                body = {
                    "author": owner,
                    "lifecycleState": "PUBLISHED",
                    "specificContent": {
                        "com.linkedin.ugc.ShareContent": {
                            "shareCommentary": {"text": message},
                            "shareMediaCategory": "IMAGE",
                            "media": [{"status": "READY", "media": asset}]
                        }
                    },
                    "visibility": {"com.linkedin.ugc.MemberNetworkVisibility": "PUBLIC"}
                }
            else:
                # Text-only post
                body = {
                    "author": owner,
                    "lifecycleState": "PUBLISHED",
                    "specificContent": {
                        "com.linkedin.ugc.ShareContent": {
                            "shareCommentary": {"text": message},
                            "shareMediaCategory": "NONE"
                        }
                    },
                    "visibility": {"com.linkedin.ugc.MemberNetworkVisibility": "PUBLIC"}
                }
            
            # Publish post
            post_resp = client.post("https://api.linkedin.com/v2/ugcPosts", headers=headers, json=body)
            post_resp.raise_for_status()
            return ""  # LinkedIn v2 API doesn't return permalink immediately
    
    result = _retry_request(_post)
    log_event("social_poster", "info", "LinkedIn post published", {"has_image": bool(image_path)})
    return result
