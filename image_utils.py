"""
image_utils.py - Image generation utilities with text detection and brand-safe filters.
Ensures generated images are text-free and comply with brand guidelines.
"""
import os
import yaml
import csv
from datetime import datetime
from typing import Optional, Tuple
from db import log_event

# Try to import easyocr, fallback to None if not installed
try:
    import easyocr
    OCR_AVAILABLE = True
    _reader = None  # Lazy load
except ImportError:
    OCR_AVAILABLE = False
    _reader = None

def get_ocr_reader():
    """Lazy load EasyOCR reader (only when needed)."""
    global _reader
    if _reader is None and OCR_AVAILABLE:
        _reader = easyocr.Reader(['en'], gpu=False, verbose=False)
    return _reader

def load_image_style_config(config_path: str = "config/image_style.yaml") -> dict:
    """Load image style configuration from YAML."""
    if not os.path.exists(config_path):
        log_event("image_utils", "warning", f"Image style config not found: {config_path}")
        return {
            "tone": "professional, minimalist, high-tech",
            "avoid": ["text", "labels", "letters"],
            "palette": ["#0A192F", "#172A45", "#64FFDA", "#E6F1FF"],
            "keywords": ["futuristic design", "digital intelligence"],
            "retries": 3
        }
    
    with open(config_path, 'r', encoding='utf-8') as f:
        data = yaml.safe_load(f)
    
    return data.get("style", {})

def build_brand_safe_prompt(base_prompt: str, style_config: dict) -> str:
    """
    Enhance base prompt with brand-safe style filters.
    Args:
        base_prompt: Original image prompt
        style_config: Style configuration dict
    Returns:
        Enhanced prompt with brand guidelines
    """
    tone = style_config.get("tone", "professional")
    avoid = style_config.get("avoid", [])
    keywords = style_config.get("keywords", [])
    
    # Build enhanced prompt
    enhanced = f"{base_prompt}. Style: {tone}"
    
    # Add positive keywords
    if keywords:
        enhanced += f", featuring {', '.join(keywords[:2])}"
    
    # Add negative constraints
    if avoid:
        enhanced += f". IMPORTANT: No {', no '.join(avoid)}, purely visual abstract design"
    
    return enhanced

def detect_text_in_image(image_path: str) -> Tuple[bool, int]:
    """
    Detect if image contains text using OCR.
    Args:
        image_path: Path to image file
    Returns:
        (has_text: bool, text_count: int)
    """
    if not OCR_AVAILABLE:
        log_event("image_utils", "warning", "EasyOCR not available, skipping text detection")
        return False, 0
    
    try:
        reader = get_ocr_reader()
        if reader is None:
            return False, 0
        
        # Perform OCR detection
        results = reader.readtext(image_path)
        
        # Filter out very low confidence detections (< 0.3)
        valid_detections = [r for r in results if r[2] > 0.3]
        
        has_text = len(valid_detections) > 0
        text_count = len(valid_detections)
        
        if has_text:
            detected_texts = [r[1] for r in valid_detections[:3]]  # First 3
            log_event("image_utils", "info", 
                     f"Text detected in image: {text_count} instances",
                     {"path": image_path, "samples": detected_texts})
        
        return has_text, text_count
        
    except Exception as e:
        log_event("image_utils", "error", f"OCR detection failed: {str(e)}")
        return False, 0

def log_image_audit(image_path: str, attempt: int, has_text: bool, 
                    text_count: int, action: str, audit_path: str = "logs/image_audit.csv"):
    """
    Log image generation audit to CSV.
    Args:
        image_path: Path to generated image
        attempt: Attempt number (1-3)
        has_text: Whether text was detected
        text_count: Number of text instances found
        action: Action taken (kept, regenerated, failed)
        audit_path: Path to audit CSV file
    """
    os.makedirs(os.path.dirname(audit_path), exist_ok=True)
    
    # Check if file exists to determine if we need header
    file_exists = os.path.exists(audit_path)
    
    with open(audit_path, 'a', newline='', encoding='utf-8') as f:
        fieldnames = ['timestamp', 'image_path', 'attempt', 'has_text', 
                     'text_count', 'action']
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        
        if not file_exists:
            writer.writeheader()
        
        writer.writerow({
            'timestamp': datetime.utcnow().strftime("%Y-%m-%d %H:%M:%S"),
            'image_path': image_path,
            'attempt': attempt,
            'has_text': 'yes' if has_text else 'no',
            'text_count': text_count,
            'action': action
        })

def validate_image_brand_safe(image_path: str, max_retries: int = 3) -> Tuple[bool, int]:
    """
    Validate that generated image is brand-safe (no text).
    Args:
        image_path: Path to image file
        max_retries: Maximum retry attempts
    Returns:
        (is_valid: bool, attempts_used: int)
    """
    has_text, text_count = detect_text_in_image(image_path)
    
    if not has_text:
        log_image_audit(image_path, 1, False, 0, "kept")
        return True, 1
    else:
        log_image_audit(image_path, 1, True, text_count, "needs_regeneration")
        return False, 1

