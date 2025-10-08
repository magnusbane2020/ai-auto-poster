import os, time, json
from datetime import datetime, timedelta
from apscheduler.schedulers.blocking import BlockingScheduler

from config import CFG
from db import get_db
from trends import discover_topics, normalize_topic
from ai_agent import bmad_supervisor, generate_text, generate_image
from guardrails import enforce_platform_rules
from social_poster import post_facebook, post_linkedin

def plan_daily():
    topics = discover_topics()
    brand = ["Romania context", "tech + educational + funny", "no fluff, clear CTA"]
    plan = bmad_supervisor(topics, brand)
    # Generate 3 variants text
    variants = generate_text(topic=topics[0], brand_bullets=brand, style=plan["body_style"], variants=3)
    best = variants["variants"][0]  # keep simple: first is best (BMAD already decided)
    # Image
    raw = generate_image(plan["image_prompt"])
    os.makedirs(CFG["MEDIA_DIR"], exist_ok=True)
    img_path = os.path.join(CFG["MEDIA_DIR"], f"post_{int(time.time())}.png")
    with open(img_path, "wb") as f: f.write(raw)

    # Prepare two platforms
    lk_body = enforce_platform_rules(best["body"], "linkedin")
    fb_body = enforce_platform_rules(best["body"], "facebook")

    with get_db() as db:
        for platform, body in (("linkedin", lk_body), ("facebook", fb_body)):
            db.execute("""INSERT INTO posts(platform,status,title,body,image_path,scheduled_at,topic_key)
                          VALUES(?,?,?,?,?,datetime('now','+1 hour'),?)""",
                       (platform, "scheduled", best["title"], body, img_path, normalize_topic(topics[0])))

def tick():
    now = datetime.utcnow()
    with get_db() as db:
        cur = db.execute("""SELECT * FROM posts
                            WHERE status='scheduled' AND scheduled_at <= datetime('now') 
                            ORDER BY id LIMIT 5""")
        rows = cur.fetchall()
        for r in rows:
            try:
                if r["platform"] == "facebook":
                    link = post_facebook(r["body"], r["image_path"])
                else:
                    link = post_linkedin(r["body"], r["image_path"])
                db.execute("UPDATE posts SET status='posted', posted_at=datetime('now'), permalink=? WHERE id=?",
                           (link, r["id"]))
            except Exception as e:
                db.execute("UPDATE posts SET status='error' WHERE id=?", (r["id"],))

if __name__ == "__main__":
    sch = BlockingScheduler(timezone=CFG["TZ"])
    # plan content daily at 08:00
    sch.add_job(plan_daily, "cron", hour=8, minute=0)
    # post when due every 2 minutes
    sch.add_job(tick, "interval", minutes=2)
    print("Scheduler running…")
    sch.start()
