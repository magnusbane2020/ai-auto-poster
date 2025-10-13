"""
linkedin_api_client.py - Official LinkedIn Community Management API client.
Supports OAuth 2.0 authentication, token refresh, and posting to organization pages.
Falls back to Selenium if API fails or is not configured.
"""
import os
import time
import json
import logging
from typing import Optional, Tuple
from datetime import datetime
import httpx
from config import CFG
from db import log_event

class LinkedInAPIClient:
    """
    LinkedIn Community Management API client (Development Tier).
    Supports posting text and images to organization pages.
    """
    
    BASE_URL = "https://api.linkedin.com/rest"
    TOKEN_URL = "https://www.linkedin.com/oauth/v2/accessToken"
    
    def __init__(self):
        self.client_id = CFG.get("LINKEDIN_CLIENT_ID", "")
        self.client_secret = CFG.get("LINKEDIN_CLIENT_SECRET", "")
        self.access_token = CFG.get("LINKEDIN_ACCESS_TOKEN", "")
        self.refresh_token = CFG.get("LINKEDIN_REFRESH_TOKEN", "")
        self.org_urn = CFG.get("LINKEDIN_ORG_URN", "")
        self.person_urn = CFG.get("LINKEDIN_PERSON_URN", "")
        
        self.enabled = bool(self.client_id and self.client_secret and self.access_token)
        
        if not self.enabled:
            log_event("linkedin_api", "info", "LinkedIn API not configured, will use Selenium fallback")
    
    def _get_headers(self) -> dict:
        """Get authentication headers for API requests."""
        return {
            "Authorization": f"Bearer {self.access_token}",
            "Content-Type": "application/json",
            "X-Restli-Protocol-Version": "2.0.0",
            "LinkedIn-Version": "202304"
        }
    
    def refresh_access_token(self) -> bool:
        """
        Refresh the LinkedIn access token using refresh token.
        
        Returns:
            True if successful, False otherwise
        """
        if not self.refresh_token:
            log_event("linkedin_api", "error", "No refresh token available")
            return False
        
        log_event("linkedin_api", "info", "Refreshing LinkedIn access token")
        
        try:
            data = {
                "grant_type": "refresh_token",
                "refresh_token": self.refresh_token,
                "client_id": self.client_id,
                "client_secret": self.client_secret
            }
            
            with httpx.Client(timeout=30) as client:
                response = client.post(self.TOKEN_URL, data=data)
                response.raise_for_status()
                
                token_data = response.json()
                new_access_token = token_data.get("access_token")
                new_refresh_token = token_data.get("refresh_token", self.refresh_token)
                
                if new_access_token:
                    # Update in-memory token
                    self.access_token = new_access_token
                    self.refresh_token = new_refresh_token
                    
                    # Update .env file
                    self._update_env_tokens(new_access_token, new_refresh_token)
                    
                    log_event("linkedin_api", "info", "LinkedIn access token refreshed successfully")
                    return True
                else:
                    log_event("linkedin_api", "error", "No access token in refresh response")
                    return False
                    
        except Exception as e:
            log_event("linkedin_api", "error", f"Token refresh failed: {str(e)}")
            return False
    
    def _update_env_tokens(self, new_access_token: str, new_refresh_token: str):
        """Update .env file with new tokens."""
        try:
            env_path = ".env"
            if not os.path.exists(env_path):
                log_event("linkedin_api", "warning", ".env file not found, cannot update tokens")
                return
            
            with open(env_path, "r", encoding="utf-8") as f:
                lines = f.readlines()
            
            updated = False
            with open(env_path, "w", encoding="utf-8") as f:
                for line in lines:
                    if line.startswith("LINKEDIN_ACCESS_TOKEN="):
                        f.write(f"LINKEDIN_ACCESS_TOKEN={new_access_token}\n")
                        updated = True
                    elif line.startswith("LINKEDIN_REFRESH_TOKEN="):
                        f.write(f"LINKEDIN_REFRESH_TOKEN={new_refresh_token}\n")
                    else:
                        f.write(line)
            
            if updated:
                log_event("linkedin_api", "info", "Tokens updated in .env file")
            
        except Exception as e:
            log_event("linkedin_api", "error", f"Failed to update .env file: {str(e)}")
    
    def upload_image(self, image_path: str) -> Optional[str]:
        """
        Upload an image to LinkedIn and return the asset URN.
        
        Args:
            image_path: Path to image file
        Returns:
            Image asset URN or None if failed
        """
        if not os.path.exists(image_path):
            log_event("linkedin_api", "error", f"Image file not found: {image_path}")
            return None
        
        try:
            # Determine owner (organization or person)
            owner = self.org_urn or self.person_urn
            if not owner:
                log_event("linkedin_api", "error", "No owner URN configured")
                return None
            
            # Step 1: Initialize upload
            init_url = f"{self.BASE_URL}/images?action=initializeUpload"
            init_payload = {
                "initializeUploadRequest": {
                    "owner": owner
                }
            }
            
            with httpx.Client(timeout=30) as client:
                init_response = client.post(init_url, headers=self._get_headers(), json=init_payload)
                init_response.raise_for_status()
                
                init_data = init_response.json()
                upload_url = init_data["value"]["uploadUrl"]
                image_urn = init_data["value"]["image"]
                
                log_event("linkedin_api", "info", f"Image upload initialized: {image_urn}")
                
                # Step 2: Upload binary data
                with open(image_path, "rb") as f:
                    upload_headers = {"Authorization": f"Bearer {self.access_token}"}
                    upload_response = client.put(upload_url, headers=upload_headers, content=f.read())
                    upload_response.raise_for_status()
                
                log_event("linkedin_api", "info", f"Image uploaded successfully: {image_path}")
                return image_urn
                
        except httpx.HTTPStatusError as e:
            if e.response.status_code == 401:
                log_event("linkedin_api", "warning", "Access token expired, attempting refresh")
                if self.refresh_access_token():
                    # Retry upload after token refresh
                    return self.upload_image(image_path)
            log_event("linkedin_api", "error", f"Image upload failed: {e.response.status_code} - {e.response.text}")
            return None
        except Exception as e:
            log_event("linkedin_api", "error", f"Image upload failed: {str(e)}")
            return None
    
    def create_post(self, text: str, image_urn: Optional[str] = None) -> Tuple[bool, str]:
        """
        Create a post on LinkedIn using the Community Management API.
        
        Args:
            text: Post text content
            image_urn: Optional image asset URN
        Returns:
            Tuple of (success: bool, post_id or error_message: str)
        """
        if not self.enabled:
            return False, "LinkedIn API not configured"
        
        try:
            # Determine author (organization or person)
            author = self.org_urn or self.person_urn
            if not author:
                return False, "No author URN configured"
            
            # Build post payload
            payload = {
                "author": author,
                "commentary": text,
                "visibility": "PUBLIC",
                "distribution": {
                    "feedDistribution": "MAIN_FEED",
                    "targetEntities": [],
                    "thirdPartyDistributionChannels": []
                },
                "lifecycleState": "PUBLISHED",
                "isReshareDisabledByAuthor": False
            }
            
            # Add image if provided
            if image_urn:
                payload["content"] = {
                    "media": {
                        "title": "Post Image",
                        "id": image_urn
                    }
                }
            
            # Make API request with retry logic
            for attempt in range(3):
                try:
                    with httpx.Client(timeout=45) as client:
                        response = client.post(
                            f"{self.BASE_URL}/posts",
                            headers=self._get_headers(),
                            json=payload
                        )
                        
                        if response.status_code == 201:
                            post_data = response.json()
                            post_id = post_data.get("id", "unknown")
                            
                            log_event("linkedin_api", "info", 
                                     f"Post created successfully via API",
                                     {"post_id": post_id, "has_image": bool(image_urn)})
                            
                            return True, post_id
                        
                        elif response.status_code == 401:
                            # Token expired, refresh and retry
                            log_event("linkedin_api", "warning", "Access token expired, refreshing")
                            if self.refresh_access_token():
                                continue  # Retry with new token
                            else:
                                return False, "Token refresh failed"
                        
                        elif response.status_code in [429, 500, 502, 503]:
                            # Rate limit or server error, retry with backoff
                            delay = 2 ** attempt
                            log_event("linkedin_api", "warning", 
                                     f"API error {response.status_code}, retrying after {delay}s (attempt {attempt+1}/3)")
                            time.sleep(delay)
                            continue
                        
                        else:
                            # Other error, don't retry
                            error_msg = f"API error {response.status_code}: {response.text}"
                            log_event("linkedin_api", "error", error_msg)
                            return False, error_msg
                
                except httpx.RequestError as e:
                    if attempt == 2:  # Last attempt
                        error_msg = f"Request failed: {str(e)}"
                        log_event("linkedin_api", "error", error_msg)
                        return False, error_msg
                    
                    delay = 2 ** attempt
                    log_event("linkedin_api", "warning", 
                             f"Request error, retrying after {delay}s (attempt {attempt+1}/3)")
                    time.sleep(delay)
            
            return False, "Max retries exceeded"
            
        except Exception as e:
            error_msg = f"Unexpected error: {str(e)}"
            log_event("linkedin_api", "error", error_msg)
            return False, error_msg
    
    def post(self, message: str, image_path: Optional[str] = None) -> Tuple[bool, str]:
        """
        High-level method to post to LinkedIn with optional image.
        
        Args:
            message: Post text content
            image_path: Optional path to image file
        Returns:
            Tuple of (success: bool, result_message: str)
        """
        if not self.enabled:
            return False, "LinkedIn API not configured"
        
        log_event("linkedin_api", "info", "Starting LinkedIn API post", 
                 {"message_length": len(message), "has_image": bool(image_path)})
        
        # Upload image if provided
        image_urn = None
        if image_path:
            image_urn = self.upload_image(image_path)
            if not image_urn:
                log_event("linkedin_api", "warning", "Image upload failed, posting text only")
        
        # Create post
        success, result = self.create_post(message, image_urn)
        
        if success:
            timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            return True, f"Posted successfully at {timestamp} (ID: {result})"
        else:
            return False, f"Post failed: {result}"


# Singleton instance
_linkedin_api_client = None

def get_linkedin_api_client() -> LinkedInAPIClient:
    """Get or create singleton LinkedIn API client instance."""
    global _linkedin_api_client
    if _linkedin_api_client is None:
        _linkedin_api_client = LinkedInAPIClient()
    return _linkedin_api_client


def post_via_linkedin_api(message: str, image_path: Optional[str] = None) -> Tuple[bool, str]:
    """
    Convenience function to post via LinkedIn API.
    
    Returns:
        Tuple of (success: bool, result_message: str)
    """
    client = get_linkedin_api_client()
    return client.post(message, image_path)


if __name__ == "__main__":
    """Test LinkedIn API client."""
    print("🔧 LinkedIn API Client Test\n")
    
    client = get_linkedin_api_client()
    
    if not client.enabled:
        print("❌ LinkedIn API not configured")
        print("\nRequired in .env:")
        print("  - LINKEDIN_CLIENT_ID")
        print("  - LINKEDIN_CLIENT_SECRET")
        print("  - LINKEDIN_ACCESS_TOKEN")
        print("  - LINKEDIN_ORG_URN or LINKEDIN_PERSON_URN")
    else:
        print("✅ LinkedIn API configured")
        print(f"  Client ID: {client.client_id[:10]}...")
        print(f"  Has access token: {bool(client.access_token)}")
        print(f"  Has refresh token: {bool(client.refresh_token)}")
        print(f"  Organization URN: {client.org_urn or 'Not set'}")
        
        # Test post
        test_message = input("\nEnter test message (or leave empty to skip): ")
        if test_message:
            success, result = client.post(test_message)
            if success:
                print(f"\n✅ {result}")
            else:
                print(f"\n❌ {result}")

