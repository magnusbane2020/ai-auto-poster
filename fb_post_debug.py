import os, json, requests
from dotenv import load_dotenv

load_dotenv()

page_id = os.getenv("FB_PAGE_ID")
token = os.getenv("FB_PAGE_ACCESS_TOKEN")

# Citește ultimul post generat
import sqlite3
conn = sqlite3.connect("posts.db")
c = conn.cursor()
c.execute("SELECT id, title, caption, image_path FROM posts ORDER BY created_at DESC LIMIT 1")
row = c.fetchone()
conn.close()

print("\n🧩 Last post in database:")
print(json.dumps({
    "id": row[0],
    "title": row[1],
    "caption": row[2],
    "image_path": row[3],
}, indent=2))

# Trimite postarea manual
message = f"{row[1]}\n\n{row[2]}"
url = f"https://graph.facebook.com/v21.0/{page_id}/photos"
files = {"source": open(row[3], "rb")} if row[3] else None
data = {"caption": message, "access_token": token}

print("\n🚀 Posting to Facebook...")
r = requests.post(url, data=data, files=files)
print("✅ Response:", r.status_code)
print(r.text)
