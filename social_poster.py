"""
social_poster.py - Publishing to Facebook and LinkedIn
Handles API authentication, image uploads, and post creation.
Implements proper error handling and retry logic for reliability.
"""
import os
from typing import Optional
import httpx
from tenacity import retry, stop_after_attempt, wait_exponential
from config import CFG
from db import log_event


@retry(
    stop=stop_after_attempt(3),
    wait=wait_exponential(multiplier=2, min=4, max=30)
)
def post_facebook(message: str, image_path: Optional[str] = None) -> str:
    """
    Post to Facebook Page.
    
    Args:
        message: Post text
        image_path: Optional path to image file
    
    Returns:
        Permalink URL to published post
    
    Raises:
        httpx.HTTPError: If API call fails after retries
    """
    page_id = CFG["FB_PAGE_ID"]
    token = CFG["FB_PAGE_ACCESS_TOKEN"]
    
    if not page_id or not token:
        raise ValueError("FB_PAGE_ID and FB_PAGE_ACCESS_TOKEN required")
    
    base_url = f"https://graph.facebook.com/v21.0/{page_id}"
    
    log_event("social_poster", "INFO", "Posting to Facebook", {"has_image": bool(image_path)})
    
    try:
        with httpx.Client(timeout=30) as client:
            if image_path and os.path.exists(image_path):
                # Upload photo with caption
                with open(image_path, "rb") as img_file:
                    files = {"source": img_file}
                    data = {"caption": message, "access_token": token}
                    response = client.post(f"{base_url}/photos", data=data, files=files)
            else:
                # Text-only post
                data = {"message": message, "access_token": token}
                response = client.post(f"{base_url}/feed", data=data)
            
            response.raise_for_status()
            result = response.json()
            
            # Extract post ID and fetch permalink
            post_id = result.get("post_id") or result.get("id")
            if not post_id:
                log_event("social_poster", "WARNING", "No post_id returned from Facebook")
                return ""
            
            # Get permalink
            permalink_response = client.get(
                f"https://graph.facebook.com/v21.0/{post_id}",
                params={"fields": "permalink_url", "access_token": token}
            )
            permalink_data = permalink_response.json()
            permalink = permalink_data.get("permalink_url", "")
            
            log_event("social_poster", "INFO", "Facebook post successful", {"post_id": post_id})
            return permalink
    
    except httpx.HTTPError as e:
        log_event("social_poster", "ERROR", f"Facebook posting failed: {e}")
        raise
    except Exception as e:
        log_event("social_poster", "ERROR", f"Unexpected error posting to Facebook: {e}")
        raise


@retry(
    stop=stop_after_attempt(3),
    wait=wait_exponential(multiplier=2, min=4, max=30)
)
def post_linkedin(message: str, image_path: Optional[str] = None) -> str:
    """
    Post to LinkedIn (personal profile or organization page).
    
    Image posting flow:
    1. Register upload with LinkedIn
    2. Upload binary image to provided URL
    3. Create UGC post with image asset reference
    
    Args:
        message: Post text
        image_path: Optional path to image file
    
    Returns:
        Post ID or empty string (LinkedIn doesn't provide immediate permalink)
    
    Raises:
        httpx.HTTPError: If API call fails after retries
    """
    token = CFG["LINKEDIN_ACCESS_TOKEN"]
    owner = CFG["LINKEDIN_ORG_URN"] or CFG["LINKEDIN_PERSON_URN"]
    
    if not token or not owner:
        raise ValueError("LINKEDIN_ACCESS_TOKEN and LINKEDIN_PERSON_URN/ORG_URN required")
    
    headers = {
        "Authorization": f"Bearer {token}",
        "X-Restli-Protocol-Version": "2.0.0",
        "Content-Type": "application/json"
    }
    
    log_event("social_poster", "INFO", "Posting to LinkedIn", {"has_image": bool(image_path)})
    
    try:
        with httpx.Client(timeout=60) as client:  # LinkedIn can be slow
            
            if image_path and os.path.exists(image_path):
                # Step 1: Register upload
                register_payload = {
                    "registerUploadRequest": {
                        "recipes": ["urn:li:digitalmediaRecipe:feedshare-image"],
                        "owner": owner,
                        "serviceRelationships": [
                            {
                                "relationshipType": "OWNER",
                                "identifier": "urn:li:userGeneratedContent"
                            }
                        ]
                    }
                }
                
                register_response = client.post(
                    "https://api.linkedin.com/v2/assets?action=registerUpload",
                    headers=headers,
                    json=register_payload
                )
                register_response.raise_for_status()
                register_data = register_response.json()
                
                upload_url = register_data["value"]["uploadMechanism"]["com.linkedin.digitalmedia.uploading.MediaUploadHttpRequest"]["uploadUrl"]
                asset_urn = register_data["value"]["asset"]
                
                # Step 2: Upload image binary
                with open(image_path, "rb") as img_file:
                    upload_response = client.put(
                        upload_url,
                        headers={"Authorization": f"Bearer {token}"},
                        content=img_file.read()
                    )
                    upload_response.raise_for_status()
                
                # Step 3: Create post with image
                post_body = {
                    "author": owner,
                    "lifecycleState": "PUBLISHED",
                    "specificContent": {
                        "com.linkedin.ugc.ShareContent": {
                            "shareCommentary": {"text": message},
                            "shareMediaCategory": "IMAGE",
                            "media": [
                                {
                                    "status": "READY",
                                    "media": asset_urn
                                }
                            ]
                        }
                    },
                    "visibility": {
                        "com.linkedin.ugc.MemberNetworkVisibility": "PUBLIC"
                    }
                }
            else:
                # Text-only post
                post_body = {
                    "author": owner,
                    "lifecycleState": "PUBLISHED",
                    "specificContent": {
                        "com.linkedin.ugc.ShareContent": {
                            "shareCommentary": {"text": message},
                            "shareMediaCategory": "NONE"
                        }
                    },
                    "visibility": {
                        "com.linkedin.ugc.MemberNetworkVisibility": "PUBLIC"
                    }
                }
            
            # Create UGC post
            post_response = client.post(
                "https://api.linkedin.com/v2/ugcPosts",
                headers=headers,
                json=post_body
            )
            post_response.raise_for_status()
            
            result = post_response.json()
            post_id = result.get("id", "")
            
            log_event("social_poster", "INFO", "LinkedIn post successful", {"post_id": post_id})
            
            # LinkedIn doesn't provide immediate permalink in response
            # TODO: Implement follow-up API call to fetch share URL if needed
            return post_id
    
    except httpx.HTTPError as e:
        log_event("social_poster", "ERROR", f"LinkedIn posting failed: {e}")
        raise
    except Exception as e:
        log_event("social_poster", "ERROR", f"Unexpected error posting to LinkedIn: {e}")
        raise


def validate_credentials() -> dict[str, bool]:
    """
    Validate social media API credentials.
    Useful for startup checks and debugging.
    
    Returns:
        {"facebook": bool, "linkedin": bool}
    """
    status = {"facebook": False, "linkedin": False}
    
    # Facebook validation
    try:
        page_id = CFG["FB_PAGE_ID"]
        token = CFG["FB_PAGE_ACCESS_TOKEN"]
        if page_id and token:
            with httpx.Client(timeout=10) as client:
                response = client.get(
                    f"https://graph.facebook.com/v21.0/{page_id}",
                    params={"fields": "name", "access_token": token}
                )
                if response.status_code == 200:
                    status["facebook"] = True
                    log_event("social_poster", "INFO", "Facebook credentials valid")
    except Exception as e:
        log_event("social_poster", "WARNING", f"Facebook validation failed: {e}")
    
    # LinkedIn validation
    try:
        token = CFG["LINKEDIN_ACCESS_TOKEN"]
        if token:
            headers = {"Authorization": f"Bearer {token}"}
            with httpx.Client(timeout=10) as client:
                response = client.get(
                    "https://api.linkedin.com/v2/me",
                    headers=headers
                )
                if response.status_code == 200:
                    status["linkedin"] = True
                    log_event("social_poster", "INFO", "LinkedIn credentials valid")
    except Exception as e:
        log_event("social_poster", "WARNING", f"LinkedIn validation failed: {e}")
    
    return status

