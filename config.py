"""
config.py - Environment-driven configuration loader
Loads all secrets and settings from .env file.
Never hardcode credentials - everything via environment variables.
"""
import os
from typing import Any
from dotenv import load_dotenv

load_dotenv()


def get_env(key: str, default: Any = "") -> Any:
    """Fetch environment variable with fallback."""
    return os.getenv(key, default)


CFG = {
    # OpenAI
    "OPENAI_API_KEY": get_env("OPENAI_API_KEY"),
    
    # Facebook
    "FB_PAGE_ID": get_env("FB_PAGE_ID"),
    "FB_PAGE_ACCESS_TOKEN": get_env("FB_PAGE_ACCESS_TOKEN"),
    
    # LinkedIn
    "LINKEDIN_ACCESS_TOKEN": get_env("LINKEDIN_ACCESS_TOKEN"),
    "LINKEDIN_PERSON_URN": get_env("LINKEDIN_PERSON_URN"),
    "LINKEDIN_ORG_URN": get_env("LINKEDIN_ORG_URN"),
    
    # Storage
    "DB_PATH": get_env("DB_PATH", "posts.db"),
    "MEDIA_DIR": get_env("MEDIA_DIR", "media"),
    
    # Scheduling
    "TZ": get_env("TZ", "Europe/Bucharest"),
    "POST_HOUR": get_env("POST_HOUR", "09:00"),
    
    # Brand
    "BRAND_NAME": get_env("BRAND_NAME", "Tech Brand"),
    "BRAND_CONTEXT": get_env("BRAND_CONTEXT", "Romania context"),
    "BRAND_STYLE": get_env("BRAND_STYLE", "tech + educational + funny"),
    
    # Trends
    "TREND_SOURCES": get_env("TREND_SOURCES", "https://news.ycombinator.com/rss").split(","),
}


def validate_config() -> list[str]:
    """Validate required configuration keys are present."""
    errors = []
    required = ["OPENAI_API_KEY", "FB_PAGE_ID", "FB_PAGE_ACCESS_TOKEN", "LINKEDIN_ACCESS_TOKEN"]
    
    for key in required:
        if not CFG.get(key):
            errors.append(f"Missing required config: {key}")
    
    if not CFG["LINKEDIN_PERSON_URN"] and not CFG["LINKEDIN_ORG_URN"]:
        errors.append("Must set either LINKEDIN_PERSON_URN or LINKEDIN_ORG_URN")
    
    return errors

