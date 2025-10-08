"""
scheduler.py - Main orchestrator for AI Auto-Poster system

HOW TO RUN LOCALLY:
1. Install dependencies:
   pip install -r requirements.txt

2. Configure environment:
   cp .env.example .env
   # Edit .env with your API keys and credentials

3. Run the scheduler:
   python scheduler.py

4. (Optional) Run one-time tasks:
   python scheduler.py --plan-now    # Generate content immediately
   python scheduler.py --post-now    # Post scheduled content now
   python scheduler.py --validate    # Check API credentials

SCHEDULE:
- Daily at 08:00: Discover trends, generate content, schedule posts
- Every 2 minutes: Check for due posts and publish them

WORKFLOW:
1. Discover trending topics from RSS feeds
2. BMAD Supervisor selects best topic + strategy
3. Generate text variants (3 options, pick best)
4. Generate image via DALL-E
5. Apply platform-specific guardrails
6. Schedule posts for LinkedIn + Facebook
7. Publish at scheduled time with retry logic

TODO/FUTURE ENHANCEMENTS:
- Add Streamlit UI for manual post approval
- Implement A/B testing across variants
- Add analytics tracking (engagement, reach)
- Support Instagram, Twitter/X
- Deduplicate similar topics across days
- Add cost budget limits per day/month
"""
import os
import time
import sys
from datetime import datetime, timedelta
from typing import Optional
from apscheduler.schedulers.blocking import BlockingScheduler

from config import CFG, validate_config
from db import get_db, log_event
from trends import discover_topics, normalize_topic, filter_used_topics
from ai_agent import bmad_supervisor, generate_text, generate_image
from guardrails import enforce_platform_rules, validate_post_content
from social_poster import post_facebook, post_linkedin, validate_credentials


def get_brand_bullets() -> list[str]:
    """Extract brand voice from config."""
    return [
        CFG.get("BRAND_CONTEXT", "Tech context"),
        CFG.get("BRAND_STYLE", "educational + funny"),
        "No fluff, clear CTA"
    ]


def plan_daily() -> None:
    """
    Daily content planning job.
    Discovers topics, generates content, schedules posts.
    """
    log_event("scheduler", "INFO", "Starting daily content planning")
    
    try:
        # 1. Discover trending topics
        all_topics = discover_topics(max_topics=15)
        
        # 2. Filter out recently used topics
        fresh_topics = filter_used_topics(all_topics, days_back=7)
        
        if not fresh_topics:
            log_event("scheduler", "WARNING", "No fresh topics available")
            return
        
        log_event("scheduler", "INFO", f"Found {len(fresh_topics)} fresh topics")
        
        # 3. Get brand context
        brand = get_brand_bullets()
        
        # 4. BMAD Supervisor strategic planning
        plan = bmad_supervisor(fresh_topics, brand)
        selected_topic = plan.get("selected_topic", fresh_topics[0])
        
        log_event("scheduler", "INFO", f"BMAD selected topic: {selected_topic[:50]}")
        
        # 5. Generate text variants
        variants = generate_text(
            topic=selected_topic,
            brand_bullets=brand,
            style=plan.get("body_style", "educational"),
            variants=3
        )
        
        # Pick best variant (first one, as BMAD already optimized prompt)
        best = variants["variants"][0]
        
        # 6. Generate image
        image_prompt = plan.get("image_prompt", f"Professional tech illustration: {selected_topic}")
        raw_image = generate_image(image_prompt)
        
        # Save image
        os.makedirs(CFG["MEDIA_DIR"], exist_ok=True)
        timestamp = int(time.time())
        img_path = os.path.join(CFG["MEDIA_DIR"], f"post_{timestamp}.png")
        with open(img_path, "wb") as f:
            f.write(raw_image)
        
        log_event("scheduler", "INFO", f"Image saved: {img_path}")
        
        # 7. Prepare platform-specific posts
        platforms = [
            ("linkedin", enforce_platform_rules(best["body"], "linkedin")),
            ("facebook", enforce_platform_rules(best["body"], "facebook"))
        ]
        
        # 8. Validate and schedule
        with get_db() as db:
            for platform, body in platforms:
                # Validate before scheduling
                errors = validate_post_content(best.get("title", ""), body, platform)
                if errors:
                    log_event("scheduler", "ERROR", f"Validation failed for {platform}: {errors}")
                    continue
                
                # Schedule post for 1 hour from now (adjust as needed)
                db.execute(
                    """INSERT INTO posts(platform, status, title, body, image_path, scheduled_at, topic_key)
                       VALUES(?, 'scheduled', ?, ?, ?, datetime('now', '+1 hour'), ?)""",
                    (platform, best.get("title", ""), body, img_path, normalize_topic(selected_topic))
                )
                
                log_event("scheduler", "INFO", f"Scheduled post for {platform}")
        
        log_event("scheduler", "INFO", "Daily planning completed successfully")
    
    except Exception as e:
        log_event("scheduler", "ERROR", f"Daily planning failed: {e}")
        raise


def tick() -> None:
    """
    Publishing job - runs frequently to check for due posts.
    Posts scheduled content when time is reached.
    """
    with get_db() as db:
        # Find posts due for publishing
        cur = db.execute(
            """SELECT * FROM posts
               WHERE status='scheduled' AND scheduled_at <= datetime('now')
               ORDER BY scheduled_at ASC
               LIMIT 5"""
        )
        rows = cur.fetchall()
        
        if not rows:
            return  # Nothing to post
        
        log_event("scheduler", "INFO", f"Found {len(rows)} posts due for publishing")
        
        for row in rows:
            post_id = row["id"]
            platform = row["platform"]
            body = row["body"]
            image_path = row["image_path"]
            
            try:
                log_event("scheduler", "INFO", f"Publishing post {post_id} to {platform}")
                
                # Publish to platform
                if platform == "facebook":
                    permalink = post_facebook(body, image_path)
                elif platform == "linkedin":
                    permalink = post_linkedin(body, image_path)
                else:
                    raise ValueError(f"Unknown platform: {platform}")
                
                # Update status
                db.execute(
                    """UPDATE posts 
                       SET status='posted', posted_at=datetime('now'), permalink=?
                       WHERE id=?""",
                    (permalink, post_id)
                )
                
                log_event("scheduler", "INFO", f"Post {post_id} published successfully", {"permalink": permalink})
            
            except Exception as e:
                # Increment retry count
                retry_count = row.get("retry_count", 0) + 1
                max_retries = 3
                
                if retry_count >= max_retries:
                    # Give up after max retries
                    db.execute(
                        """UPDATE posts 
                           SET status='error', error_message=?, retry_count=?
                           WHERE id=?""",
                        (str(e)[:500], retry_count, post_id)
                    )
                    log_event("scheduler", "ERROR", f"Post {post_id} failed permanently: {e}")
                else:
                    # Reschedule for retry
                    db.execute(
                        """UPDATE posts 
                           SET retry_count=?, error_message=?, scheduled_at=datetime('now', '+10 minutes')
                           WHERE id=?""",
                        (retry_count, str(e)[:500], post_id)
                    )
                    log_event("scheduler", "WARNING", f"Post {post_id} failed, will retry ({retry_count}/{max_retries}): {e}")


def startup_checks() -> bool:
    """
    Validate configuration and credentials before starting.
    
    Returns:
        True if all checks pass, False otherwise
    """
    print("🔍 Running startup checks...")
    
    # Check config
    config_errors = validate_config()
    if config_errors:
        print("❌ Configuration errors:")
        for error in config_errors:
            print(f"  - {error}")
        return False
    
    print("✅ Configuration valid")
    
    # Check credentials
    creds = validate_credentials()
    print(f"📘 Facebook: {'✅' if creds['facebook'] else '❌'}")
    print(f"💼 LinkedIn: {'✅' if creds['linkedin'] else '❌'}")
    
    if not any(creds.values()):
        print("❌ No valid social media credentials found")
        return False
    
    print("✅ Startup checks passed\n")
    return True


def main():
    """Main entry point."""
    # Handle CLI arguments
    if len(sys.argv) > 1:
        cmd = sys.argv[1]
        
        if cmd == "--plan-now":
            print("📝 Running content planning now...")
            plan_daily()
            print("✅ Planning complete")
            return
        
        elif cmd == "--post-now":
            print("📤 Publishing scheduled posts now...")
            tick()
            print("✅ Publishing complete")
            return
        
        elif cmd == "--validate":
            startup_checks()
            return
        
        else:
            print(f"Unknown command: {cmd}")
            print("Available commands: --plan-now, --post-now, --validate")
            return
    
    # Normal scheduled operation
    if not startup_checks():
        print("❌ Startup checks failed. Fix configuration and try again.")
        sys.exit(1)
    
    # Create scheduler
    scheduler = BlockingScheduler(timezone=CFG["TZ"])
    
    # Schedule daily content planning
    hour, minute = CFG["POST_HOUR"].split(":")
    scheduler.add_job(plan_daily, "cron", hour=int(hour), minute=int(minute))
    print(f"📅 Daily planning scheduled for {CFG['POST_HOUR']} {CFG['TZ']}")
    
    # Schedule publishing checks
    scheduler.add_job(tick, "interval", minutes=2)
    print("📤 Publishing check every 2 minutes")
    
    # Start scheduler
    print(f"\n🚀 AI Auto-Poster scheduler running...")
    print("Press Ctrl+C to stop\n")
    
    log_event("scheduler", "INFO", "Scheduler started")
    
    try:
        scheduler.start()
    except (KeyboardInterrupt, SystemExit):
        print("\n👋 Scheduler stopped")
        log_event("scheduler", "INFO", "Scheduler stopped by user")


if __name__ == "__main__":
    main()

