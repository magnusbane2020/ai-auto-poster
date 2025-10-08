"""
scheduler.py - APScheduler-based job orchestration.

=== HOW TO RUN LOCALLY ===

1. Setup environment:
   ```bash
   python3 -m venv .venv
   source .venv/bin/activate  # On Windows: .venv\\Scripts\\activate
   pip install -r requirements.txt
   ```

2. Configure .env file (copy from .env.example):
   ```bash
   cp .env.example .env
   # Edit .env with your API keys and tokens
   ```

3. Run scheduler:
   ```bash
   python scheduler.py
   ```
   
   This starts two jobs:
   - plan_daily: Runs daily at 08:00 (discovers topics, generates content)
   - tick: Runs every 2 minutes (publishes scheduled posts)

4. Monitor logs:
   ```bash
   sqlite3 posts.db "SELECT * FROM logs ORDER BY id DESC LIMIT 20;"
   ```

5. Check costs:
   ```bash
   sqlite3 posts.db "SELECT date, SUM(cost_usd) FROM costs GROUP BY date;"
   ```

=== ARCHITECTURE ===
- Idempotent jobs: Safe to restart, no duplicate posts
- Retry logic: Exponential backoff on API failures
- Cost tracking: Enforces daily/monthly budget limits
- Caching: Minimizes duplicate API calls

TODO: Add Streamlit dashboard for manual triggers and analytics
TODO: Add deduplication for topics (fuzzy matching)
TODO: Add A/B testing for post variants
"""
import os
import time
import json
from datetime import datetime
from apscheduler.schedulers.blocking import BlockingScheduler

from config import CFG, validate_config
from db import get_db, log_event
from trends import discover_topics, normalize_topic
from ai_agent import bmad_supervisor, generate_text, generate_image
from guardrails import enforce_platform_rules, validate_post_content
from social_poster import post_facebook, post_linkedin

def plan_daily():
    """
    Daily content planning job.
    1. Discovers trending topics
    2. BMAD Supervisor selects best strategy
    3. Generates text variants
    4. Generates image
    5. Schedules posts for both platforms
    """
    log_event("scheduler", "info", "Starting daily content planning")
    
    try:
        # Discover topics
        topics = discover_topics(max_topics=10)
        if not topics:
            log_event("scheduler", "error", "No topics discovered")
            return
        
        # Get brand voice from config
        brand = CFG["BRAND_BULLETS"]
        
        # BMAD Supervisor decision
        plan = bmad_supervisor(topics, brand)
        log_event("scheduler", "info", f"Supervisor selected: {plan.get('title', 'N/A')[:50]}")
        
        # Generate text variants
        variants = generate_text(
            topic=topics[0],
            brand_bullets=brand,
            style=plan.get("body_style", "professional"),
            variants=3
        )
        
        # Select best variant (first one is typically best due to temperature)
        best = variants.get("variants", [{}])[0]
        if not best.get("body"):
            log_event("scheduler", "error", "No valid text variant generated")
            return
        
        # Validate content
        errors = validate_post_content(best.get("title", ""), best["body"])
        if errors:
            log_event("scheduler", "warning", f"Content validation issues: {', '.join(errors)}")
        
        # Generate image
        os.makedirs(CFG["MEDIA_DIR"], exist_ok=True)
        img_path = os.path.join(CFG["MEDIA_DIR"], f"post_{int(time.time())}.png")
        raw = generate_image(plan.get("image_prompt", "Abstract professional design"), save_path=img_path)
        
        # Apply platform-specific guardrails
        lk_body = enforce_platform_rules(best["body"], "linkedin")
        fb_body = enforce_platform_rules(best["body"], "facebook")
        
        # Schedule posts (1 hour from now for review buffer)
        with get_db() as db:
            for platform, body in [("linkedin", lk_body), ("facebook", fb_body)]:
                db.execute(
                    """INSERT INTO posts(platform, status, title, body, image_path, scheduled_at, topic_key)
                       VALUES(?, ?, ?, ?, ?, datetime('now', '+1 hour'), ?)""",
                    (platform, "scheduled", best.get("title", ""), body, img_path, normalize_topic(topics[0]))
                )
        
        log_event("scheduler", "info", "Daily content planning completed", {
            "topics_count": len(topics),
            "title": best.get("title", "")[:50]
        })
        
    except Exception as e:
        log_event("scheduler", "error", f"Daily planning failed: {str(e)}", {"exception": str(e)})
        raise

def tick():
    """
    Posting tick job (runs every 2 minutes).
    Publishes scheduled posts that are due.
    Implements retry logic with max 3 attempts per post.
    """
    with get_db() as db:
        cur = db.execute(
            """SELECT * FROM posts
               WHERE status IN ('scheduled', 'error') 
               AND scheduled_at <= datetime('now')
               AND retry_count < 3
               ORDER BY scheduled_at ASC LIMIT 5"""
        )
        rows = cur.fetchall()
        
        if not rows:
            return  # Nothing to post
        
        log_event("scheduler", "info", f"Processing {len(rows)} scheduled posts")
        
        for post in rows:
            post_id = post["id"]
            platform = post["platform"]
            
            try:
                # Publish to platform
                if platform == "facebook":
                    permalink = post_facebook(post["body"], post["image_path"])
                elif platform == "linkedin":
                    permalink = post_linkedin(post["body"], post["image_path"])
                else:
                    raise ValueError(f"Unknown platform: {platform}")
                
                # Mark as posted
                db.execute(
                    """UPDATE posts 
                       SET status='posted', posted_at=datetime('now'), permalink=?, error_message=NULL
                       WHERE id=?""",
                    (permalink, post_id)
                )
                
                log_event("scheduler", "info", f"{platform.capitalize()} post published", {
                    "post_id": post_id,
                    "title": post["title"][:50] if post["title"] else None
                })
                
            except Exception as e:
                # Increment retry count and log error
                retry_count = post["retry_count"] + 1
                db.execute(
                    """UPDATE posts 
                       SET status='error', retry_count=?, error_message=?
                       WHERE id=?""",
                    (retry_count, str(e)[:500], post_id)
                )
                
                log_event("scheduler", "error", f"Failed to post to {platform}", {
                    "post_id": post_id,
                    "retry_count": retry_count,
                    "error": str(e)[:200]
                })

def run_scheduler():
    """
    Start the APScheduler with configured jobs.
    """
    # Validate config on startup
    config_errors = validate_config()
    if config_errors:
        print(f"❌ Configuration errors: {', '.join(config_errors)}")
        print("Please check your .env file.")
        return
    
    print("✅ Configuration validated")
    print(f"📂 Database: {CFG['DB_PATH']}")
    print(f"📁 Media directory: {CFG['MEDIA_DIR']}")
    print(f"🌍 Timezone: {CFG['TZ']}")
    
    sch = BlockingScheduler(timezone=CFG["TZ"])
<<<<<<< Current (Your changes)
    # plan content daily at 08:00
    sch.add_job(plan_daily, "cron", hour=8, minute=0)
    # post when due every 2 minutes
    sch.add_job(tick, "interval", minutes=2)
    print("Scheduler running…")
    sch.start()
=======
    
    # Daily content planning at 08:00
    sch.add_job(plan_daily, "cron", hour=8, minute=0, id="daily_planning")
    
    # Check for posts to publish every 2 minutes
    sch.add_job(tick, "interval", minutes=2, id="posting_tick")
    
    log_event("scheduler", "info", "Scheduler started")
    print("⏰ Scheduler running...")
    print("   - Daily planning: 08:00")
    print("   - Posting tick: every 2 minutes")
    print("Press Ctrl+C to stop.")
    
    try:
        sch.start()
    except (KeyboardInterrupt, SystemExit):
        print("\n👋 Scheduler stopped")
        log_event("scheduler", "info", "Scheduler stopped by user")

if __name__ == "__main__":
    run_scheduler()
>>>>>>> Incoming (Background Agent changes)
