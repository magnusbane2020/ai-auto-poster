"""
config.py - Centralized configuration from environment variables.
All secrets and tunables loaded from .env file.
Never hardcode credentials.
"""
import os
from dotenv import load_dotenv

load_dotenv()

CFG = {
    "OPENAI_API_KEY": os.getenv("OPENAI_API_KEY", ""),
    "FB_PAGE_ID": os.getenv("FB_PAGE_ID", ""),
    "FB_PAGE_ACCESS_TOKEN": os.getenv("FB_PAGE_ACCESS_TOKEN", ""),
    "LINKEDIN_ACCESS_TOKEN": os.getenv("LINKEDIN_ACCESS_TOKEN", ""),
    "LINKEDIN_PERSON_URN": os.getenv("LINKEDIN_PERSON_URN"),
    "LINKEDIN_ORG_URN": os.getenv("LINKEDIN_ORG_URN"),
    "DB_PATH": os.getenv("DB_PATH", "posts.db"),
    "MEDIA_DIR": os.getenv("MEDIA_DIR", "media"),
    "TZ": os.getenv("TZ", "Europe/Bucharest"),
    "POST_HOUR": os.getenv("POST_HOUR", "09:00"),
    "DAILY_COST_LIMIT_USD": float(os.getenv("DAILY_COST_LIMIT_USD", "5.0")),
    "MONTHLY_COST_LIMIT_USD": float(os.getenv("MONTHLY_COST_LIMIT_USD", "100.0")),
    "BRAND_BULLETS": os.getenv("BRAND_BULLETS", "Romania context,tech + educational,no fluff").split(","),
    # Canva API Integration
    "CANVA_API_KEY": os.getenv("CANVA_API_KEY", ""),
    "CANVA_TEAM_ID": os.getenv("CANVA_TEAM_ID", ""),
    "CANVA_BRAND_TEMPLATE_ID": os.getenv("CANVA_BRAND_TEMPLATE_ID", ""),
    "USE_CANVA": os.getenv("USE_CANVA", "false").lower() in ("true", "1", "yes"),
    # v3.0: LinkedIn Selenium Automation (bypasses API requirements)
    "USE_LINKEDIN_SELENIUM": os.getenv("USE_LINKEDIN_SELENIUM", "true").lower() in ("true", "1", "yes"),
    # v3.1: LinkedIn Official API (Community Management API)
    "LINKEDIN_CLIENT_ID": os.getenv("LINKEDIN_CLIENT_ID", ""),
    "LINKEDIN_CLIENT_SECRET": os.getenv("LINKEDIN_CLIENT_SECRET", ""),
    "LINKEDIN_REFRESH_TOKEN": os.getenv("LINKEDIN_REFRESH_TOKEN", ""),
    "PREFER_LINKEDIN_API": os.getenv("PREFER_LINKEDIN_API", "true").lower() in ("true", "1", "yes"),
}

def validate_config() -> list[str]:
    """Return list of missing critical env vars."""
    errors = []
    if not CFG["OPENAI_API_KEY"]:
        errors.append("OPENAI_API_KEY")
    if not CFG["FB_PAGE_ID"] or not CFG["FB_PAGE_ACCESS_TOKEN"]:
        errors.append("FB_PAGE_ID or FB_PAGE_ACCESS_TOKEN")
    if not CFG["LINKEDIN_ACCESS_TOKEN"]:
        errors.append("LINKEDIN_ACCESS_TOKEN")
    if not CFG["LINKEDIN_PERSON_URN"] and not CFG["LINKEDIN_ORG_URN"]:
        errors.append("LINKEDIN_PERSON_URN or LINKEDIN_ORG_URN")
    # Canva is optional but warn if enabled without credentials
    if CFG["USE_CANVA"] and not CFG["CANVA_API_KEY"]:
        errors.append("CANVA_API_KEY (required when USE_CANVA=true)")
    return errors
