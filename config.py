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
}
