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
<<<<<<< Current (Your changes)
}
=======
    "DAILY_COST_LIMIT_USD": float(os.getenv("DAILY_COST_LIMIT_USD", "5.0")),
    "MONTHLY_COST_LIMIT_USD": float(os.getenv("MONTHLY_COST_LIMIT_USD", "100.0")),
    "BRAND_BULLETS": os.getenv("BRAND_BULLETS", "Romania context,tech + educational,no fluff").split(","),
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
    return errors
>>>>>>> Incoming (Background Agent changes)
