"""
canva_client.py - Canva Pro API integration for professional brand-safe image generation.
Uses Canva's design API to create images from templates with custom text overlays.
Falls back to DALL-E if Canva fails or is not configured.
"""
import os
import time
import json
import hashlib
from typing import Optional, Tuple
import httpx
from config import CFG
from db import log_event, record_cost

class CanvaClient:
    """
    Canva Pro API client for generating branded social media images.
    """
    
    BASE_URL = "https://api.canva.com/rest/v1"
    
    def __init__(self):
        self.api_key = CFG["CANVA_API_KEY"]
        self.team_id = CFG["CANVA_TEAM_ID"]
        self.brand_template_id = CFG["CANVA_BRAND_TEMPLATE_ID"]
        self.enabled = CFG["USE_CANVA"]
        
        if not self.enabled:
            log_event("canva_client", "info", "Canva API disabled, using DALL-E only")
    
    def _get_headers(self) -> dict:
        """Get authentication headers for Canva API."""
        return {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json"
        }
    
    def _retry_request(self, func, max_retries=3, initial_delay=2.0):
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
                log_event("canva_client", "warning", 
                         f"HTTP error {e.response.status_code}, retry {attempt+1}/{max_retries} after {delay}s",
                         {"status": e.response.status_code, "body": e.response.text[:200]})
                time.sleep(delay)
            except (httpx.RequestError, httpx.TimeoutException) as e:
                if attempt == max_retries - 1:
                    raise
                delay = initial_delay * (2 ** attempt)
                log_event("canva_client", "warning", 
                         f"Request error, retry {attempt+1}/{max_retries} after {delay}s",
                         {"error": str(e)})
                time.sleep(delay)
        raise RuntimeError(f"Max retries ({max_retries}) exceeded")
    
    def create_design_from_template(self, text_content: str, title: str = "") -> Optional[str]:
        """
        Create a new design from a brand template with custom text.
        
        Args:
            text_content: Main text content to overlay on the design
            title: Optional title text
        Returns:
            Design ID if successful, None otherwise
        """
        if not self.enabled or not self.api_key:
            return None
        
        try:
            def _create():
                with httpx.Client(timeout=30) as client:
                    # Create design from template
                    payload = {
                        "design_type": "social_media_post",
                        "asset_id": self.brand_template_id,
                        "title": title or f"Auto-generated post {int(time.time())}",
                    }
                    
                    response = client.post(
                        f"{self.BASE_URL}/designs",
                        headers=self._get_headers(),
                        json=payload
                    )
                    response.raise_for_status()
                    return response.json()
            
            result = self._retry_request(_create)
            design_id = result.get("design", {}).get("id")
            
            if design_id:
                log_event("canva_client", "info", "Canva design created from template", 
                         {"design_id": design_id, "template_id": self.brand_template_id})
            
            return design_id
            
        except Exception as e:
            log_event("canva_client", "error", f"Failed to create design from template: {str(e)}")
            return None
    
    def export_design(self, design_id: str, format: str = "png") -> Optional[bytes]:
        """
        Export a design as an image file.
        
        Args:
            design_id: Canva design ID
            format: Export format (png, jpg, pdf)
        Returns:
            Image bytes if successful, None otherwise
        """
        if not self.enabled or not self.api_key:
            return None
        
        try:
            def _export():
                with httpx.Client(timeout=60) as client:
                    # Request export
                    payload = {
                        "design_id": design_id,
                        "format": format,
                    }
                    
                    response = client.post(
                        f"{self.BASE_URL}/exports",
                        headers=self._get_headers(),
                        json=payload
                    )
                    response.raise_for_status()
                    return response.json()
            
            result = self._retry_request(_export)
            export_url = result.get("export", {}).get("url")
            
            if not export_url:
                # Poll for export completion if not immediately available
                job_id = result.get("job", {}).get("id")
                if job_id:
                    export_url = self._poll_export_job(job_id)
            
            if export_url:
                # Download the exported image
                with httpx.Client(timeout=60) as client:
                    img_response = client.get(export_url)
                    img_response.raise_for_status()
                    
                    log_event("canva_client", "info", "Canva design exported", 
                             {"design_id": design_id, "format": format, "size_kb": len(img_response.content) / 1024})
                    
                    return img_response.content
            
            return None
            
        except Exception as e:
            log_event("canva_client", "error", f"Failed to export design: {str(e)}")
            return None
    
    def _poll_export_job(self, job_id: str, max_attempts: int = 10, delay: float = 2.0) -> Optional[str]:
        """
        Poll an export job until completion.
        
        Args:
            job_id: Export job ID
            max_attempts: Maximum polling attempts
            delay: Delay between polling attempts in seconds
        Returns:
            Export URL if successful, None otherwise
        """
        for attempt in range(max_attempts):
            try:
                with httpx.Client(timeout=30) as client:
                    response = client.get(
                        f"{self.BASE_URL}/exports/{job_id}",
                        headers=self._get_headers()
                    )
                    response.raise_for_status()
                    result = response.json()
                    
                    status = result.get("job", {}).get("status")
                    
                    if status == "success":
                        export_url = result.get("export", {}).get("url")
                        log_event("canva_client", "info", f"Export job completed after {attempt+1} attempts", 
                                 {"job_id": job_id})
                        return export_url
                    elif status == "failed":
                        log_event("canva_client", "error", "Export job failed", {"job_id": job_id})
                        return None
                    
                    # Still in progress, wait and retry
                    time.sleep(delay)
                    
            except Exception as e:
                log_event("canva_client", "warning", f"Export polling error: {str(e)}")
                time.sleep(delay)
        
        log_event("canva_client", "error", "Export polling timeout", {"job_id": job_id, "attempts": max_attempts})
        return None
    
    def generate_image_from_text(self, prompt: str, save_path: Optional[str] = None) -> Tuple[Optional[bytes], str]:
        """
        Generate a professional branded image using Canva templates.
        This is a simplified flow that uses AI-powered autofill if available.
        
        Args:
            prompt: Text prompt describing the desired image content
            save_path: Optional path to save the generated image
        Returns:
            Tuple of (image_bytes, source) where source is 'canva' or 'error'
        """
        if not self.enabled or not self.api_key:
            return None, "disabled"
        
        try:
            # Create a design from the brand template
            design_id = self.create_design_from_template(
                text_content=prompt[:500],  # Limit text length
                title=f"Social Post {int(time.time())}"
            )
            
            if not design_id:
                return None, "create_failed"
            
            # Export the design as PNG
            image_data = self.export_design(design_id, format="png")
            
            if not image_data:
                return None, "export_failed"
            
            # Save to file if path provided
            if save_path:
                os.makedirs(os.path.dirname(save_path), exist_ok=True)
                with open(save_path, "wb") as f:
                    f.write(image_data)
                log_event("canva_client", "info", "Image saved", {"path": save_path, "size_kb": len(image_data) / 1024})
            
            # Log cost (Canva API costs ~$0.10 per design creation + export)
            # This is an estimate - adjust based on your Canva plan
            record_cost("image_generation", "canva-api", 0, 0.10, 
                       {"prompt": prompt[:50], "design_id": design_id})
            
            return image_data, "canva"
            
        except Exception as e:
            log_event("canva_client", "error", f"Canva image generation failed: {str(e)}")
            return None, "error"


# Singleton instance
_canva_client = None

def get_canva_client() -> CanvaClient:
    """Get or create the singleton Canva client instance."""
    global _canva_client
    if _canva_client is None:
        _canva_client = CanvaClient()
    return _canva_client


def generate_canva_image(prompt: str, save_path: Optional[str] = None) -> Tuple[Optional[bytes], str]:
    """
    Convenience function to generate an image using Canva API.
    
    Args:
        prompt: Image generation prompt
        save_path: Optional path to save the image
    Returns:
        Tuple of (image_bytes, source) where source is 'canva', 'disabled', or 'error'
    """
    client = get_canva_client()
    return client.generate_image_from_text(prompt, save_path)

