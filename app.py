"""
app.py - Main entry point and CLI interface for AI Auto-Poster.

Usage:
  python app.py schedule           # Run scheduler (blocking)
  python app.py plan-now            # Trigger content planning immediately
  python app.py post-now            # Publish scheduled posts immediately
  python app.py status              # Show system status
  python app.py costs               # Show cost breakdown
  python app.py logs [--limit N]    # Show recent logs

TODO: Add Streamlit web UI for:
  - Manual post creation/editing
  - Analytics dashboard
  - Cost tracking visualization
  - Scheduled posts management
"""
import sys
import argparse
from datetime import datetime, timedelta
import os

from config import CFG, validate_config
from db import get_db, log_event
from scheduler import plan_daily, tick, run_scheduler
from csv_logger import export_posts_to_csv, get_posting_stats
from personas import get_persona_manager

def cmd_schedule():
    """Run the scheduler (blocking)."""
    run_scheduler()

def cmd_plan_now():
    """Trigger content planning immediately."""
    print("🔄 Running content planning...")
    try:
        plan_daily()
        print("✅ Content planning completed")
    except Exception as e:
        print(f"❌ Error: {e}")
        sys.exit(1)

def cmd_post_now():
    """Publish scheduled posts immediately."""
    print("🔄 Publishing scheduled posts...")
    try:
        tick()
        print("✅ Publishing completed")
    except Exception as e:
        print(f"❌ Error: {e}")
        sys.exit(1)

def cmd_status():
    """Show system status."""
    print("=== AI Auto-Poster Status ===\n")
    
    # Config validation
    errors = validate_config()
    if errors:
        print(f"⚠️  Configuration issues: {', '.join(errors)}")
    else:
        print("✅ Configuration: OK")
    
    # Database stats
    with get_db() as db:
        # Posts by status
        cur = db.execute("SELECT status, COUNT(*) as cnt FROM posts GROUP BY status")
        posts = {row["status"]: row["cnt"] for row in cur.fetchall()}
        
        print(f"\n📊 Posts:")
        print(f"   Scheduled: {posts.get('scheduled', 0)}")
        print(f"   Posted: {posts.get('posted', 0)}")
        print(f"   Error: {posts.get('error', 0)}")
        
        # Next scheduled post
        cur = db.execute(
            "SELECT scheduled_at, platform, title FROM posts WHERE status='scheduled' ORDER BY scheduled_at LIMIT 1"
        )
        next_post = cur.fetchone()
        if next_post:
            print(f"\n⏰ Next post:")
            print(f"   Time: {next_post['scheduled_at']}")
            print(f"   Platform: {next_post['platform']}")
            print(f"   Title: {next_post['title'][:50] if next_post['title'] else 'N/A'}")
        
        # Today's costs
        today = datetime.utcnow().strftime("%Y-%m-%d")
        cur = db.execute("SELECT SUM(cost_usd) as total FROM costs WHERE date=?", (today,))
        daily_cost = cur.fetchone()["total"] or 0.0
        
        # Month's costs
        month_start = datetime.utcnow().replace(day=1).strftime("%Y-%m-%d")
        cur = db.execute("SELECT SUM(cost_usd) as total FROM costs WHERE date>=?", (month_start,))
        monthly_cost = cur.fetchone()["total"] or 0.0
        
        print(f"\n💰 Costs:")
        print(f"   Today: ${daily_cost:.4f} / ${CFG['DAILY_COST_LIMIT_USD']}")
        print(f"   Month: ${monthly_cost:.4f} / ${CFG['MONTHLY_COST_LIMIT_USD']}")

def cmd_costs(args):
    """Show cost breakdown."""
    print("=== Cost Breakdown ===\n")
    
    with get_db() as db:
        # Last 7 days
        cur = db.execute("""
            SELECT date, SUM(cost_usd) as total, COUNT(*) as calls
            FROM costs
            WHERE date >= date('now', '-7 days')
            GROUP BY date
            ORDER BY date DESC
        """)
        
        print("Last 7 days:")
        for row in cur.fetchall():
            print(f"  {row['date']}: ${row['total']:.4f} ({row['calls']} API calls)")
        
        # By model
        cur = db.execute("""
            SELECT model, SUM(cost_usd) as total, SUM(tokens) as tokens
            FROM costs
            WHERE date >= date('now', '-30 days')
            GROUP BY model
            ORDER BY total DESC
        """)
        
        print("\nLast 30 days by model:")
        for row in cur.fetchall():
            print(f"  {row['model']}: ${row['total']:.4f} ({row['tokens'] or 0} tokens)")

def cmd_logs(args):
    """Show recent logs."""
    limit = args.limit if args.limit else 20
    
    with get_db() as db:
        cur = db.execute(
            "SELECT * FROM logs ORDER BY id DESC LIMIT ?",
            (limit,)
        )
        
        print(f"=== Last {limit} Log Entries ===\n")
        for row in cur.fetchall():
            level_emoji = {"info": "ℹ️", "warning": "⚠️", "error": "❌"}.get(row["level"], "•")
            print(f"{level_emoji} [{row['created_at']}] {row['scope']}: {row['message']}")

def cmd_export_csv(args):
    """Export posts to CSV."""
    output = args.output if args.output else "logs/posts_log.csv"
    print(f"📝 Exporting posts to {output}...")
    
    try:
        export_posts_to_csv(output)
        
        # Show stats
        stats = get_posting_stats()
        print(f"\n✅ Export completed!")
        print(f"\n📊 Statistics:")
        print(f"   Total posted: {stats['by_status'].get('posted', {}).get('count', 0)}")
        print(f"   Success rate: {stats['success_rate']:.1f}%")
        print(f"\n   By platform:")
        for platform, count in stats.get('by_platform', {}).items():
            print(f"     {platform.capitalize()}: {count}")
        
        print(f"\n📁 File: {output}")
    except Exception as e:
        print(f"❌ Error: {e}")
        sys.exit(1)

def cmd_personas(args):
    """Show loaded personas and their configuration."""
    print("=== Persona Configuration ===\n")
    
    try:
        pm = get_persona_manager()
        personas = pm.list_personas()
        
        print(f"Loaded {len(personas)} personas:\n")
        
        for p in personas:
            print(f"> {p.name}")
            print(f"   ID: {p.id}")
            print(f"   Weight: {p.weight * 100:.0f}%")
            print(f"   Tone: {p.tone}")
            print(f"   Style: {p.style}")
            print(f"   Sources: {len(p.sources)} RSS feeds")
            if p.keywords:
                print(f"   Keywords: {', '.join(p.keywords[:5])}")
            print(f"   Description: {p.description[:100]}...")
            print()
        
        # Test weighted selection
        if args.test:
            print("Testing weighted selection (100 samples):\n")
            selections = {}
            for _ in range(100):
                persona = pm.select_persona()
                selections[persona.id] = selections.get(persona.id, 0) + 1
            
            for p in personas:
                count = selections.get(p.id, 0)
                print(f"   {p.name}: {count}% (expected {p.weight * 100:.0f}%)")
        
    except Exception as e:
        print(f"Error loading personas: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)

def cmd_schedule_preview(args):
    """Show scheduled posts preview dashboard."""
    import json
    from collections import defaultdict
    
    print("=" * 60)
    print("Magnusbane AI Auto-Poster - Schedule Preview")
    print("=" * 60)
    print()
    
    try:
        with get_db() as db:
            # Fetch scheduled posts
            days_limit = args.days if args.days else 30
            cur = db.execute("""
                SELECT id, platform, status, title, body, image_path, 
                       scheduled_at, topic_key, created_at
                FROM posts
                WHERE status IN ('scheduled', 'pending')
                AND scheduled_at >= datetime('now')
                AND scheduled_at <= datetime('now', '+' || ? || ' days')
                ORDER BY scheduled_at ASC
            """, (days_limit,))
            
            posts = cur.fetchall()
            
            if not posts:
                print("No scheduled posts found.")
                return
            
            # Group by day
            by_day = defaultdict(list)
            for post in posts:
                scheduled_dt = datetime.strptime(post["scheduled_at"], "%Y-%m-%d %H:%M:%S")
                day_key = scheduled_dt.strftime("%Y-%m-%d")
                by_day[day_key].append(post)
            
            # Export to JSON if requested
            if args.json:
                export_data = []
                for post in posts:
                    # Extract persona from topic_key (format: persona_id:hash)
                    persona_id = post["topic_key"].split(":")[0] if post["topic_key"] else "unknown"
                    
                    export_data.append({
                        "id": post["id"],
                        "scheduled_at": post["scheduled_at"],
                        "platform": post["platform"],
                        "persona": persona_id,
                        "title": post["title"],
                        "caption": post["body"][:100] if post["body"] else "",
                        "image": post["image_path"],
                        "status": post["status"]
                    })
                
                json_path = "logs/schedule_preview.json"
                os.makedirs("logs", exist_ok=True)
                with open(json_path, 'w', encoding='utf-8') as f:
                    json.dump(export_data, f, indent=2, ensure_ascii=False)
                
                print(f"Schedule exported to: {json_path}\n")
            
            # Display schedule
            total_posts = len(posts)
            print(f"Found {total_posts} scheduled post(s) in next {days_limit} days:\n")
            
            for day in sorted(by_day.keys()):
                day_posts = by_day[day]
                day_dt = datetime.strptime(day, "%Y-%m-%d")
                day_name = day_dt.strftime("%A, %B %d, %Y")
                
                print(f"--- {day_name} ---")
                print()
                
                for post in day_posts:
                    scheduled_dt = datetime.strptime(post["scheduled_at"], "%Y-%m-%d %H:%M:%S")
                    time_str = scheduled_dt.strftime("%H:%M")
                    
                    # Extract persona from topic_key
                    persona_id = post["topic_key"].split(":")[0] if post["topic_key"] else "unknown"
                    persona_name = persona_id.replace("_", " ").title()
                    
                    # Get image status
                    img_status = "With Image" if post["image_path"] else "Text Only"
                    
                    # Truncate caption
                    caption = (post["body"][:60] + "...") if post["body"] and len(post["body"]) > 60 else (post["body"] or "")
                    
                    print(f"  [{time_str}] {post['platform'].upper():10} | {persona_name:30} | {img_status:12}")
                    print(f"           Title: {post['title'] or 'N/A'}")
                    print(f"           Caption: {caption}")
                    if post["image_path"]:
                        print(f"           Image: {os.path.basename(post['image_path'])}")
                    print(f"           Status: {post['status']}")
                    print()
            
            print("=" * 60)
            
    except Exception as e:
        print(f"Error: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)

def main():
    parser = argparse.ArgumentParser(description="AI Auto-Poster - Social media automation")
    subparsers = parser.add_subparsers(dest="command", help="Command to run")
    
    # Commands
    subparsers.add_parser("schedule", help="Run scheduler (blocking)")
    subparsers.add_parser("plan-now", help="Trigger content planning immediately")
    subparsers.add_parser("post-now", help="Publish scheduled posts immediately")
    subparsers.add_parser("status", help="Show system status")
    
    costs_parser = subparsers.add_parser("costs", help="Show cost breakdown")
    
    logs_parser = subparsers.add_parser("logs", help="Show recent logs")
    logs_parser.add_argument("--limit", type=int, default=20, help="Number of log entries")
    
    export_parser = subparsers.add_parser("export-csv", help="Export posts to CSV")
    export_parser.add_argument("--output", type=str, default="logs/posts_log.csv", help="Output CSV path")
    
    personas_parser = subparsers.add_parser("personas", help="Show persona configuration")
    personas_parser.add_argument("--test", action="store_true", help="Test weighted selection")
    
    preview_parser = subparsers.add_parser("schedule-preview", help="Show scheduled posts preview")
    preview_parser.add_argument("--days", type=int, default=7, help="Days to preview (default: 7)")
    preview_parser.add_argument("--json", action="store_true", help="Export to logs/schedule_preview.json")
    
    args = parser.parse_args()
    
    if not args.command:
        parser.print_help()
        sys.exit(1)
    
    # Route commands
    commands = {
        "schedule": lambda: cmd_schedule(),
        "plan-now": lambda: cmd_plan_now(),
        "post-now": lambda: cmd_post_now(),
        "status": lambda: cmd_status(),
        "costs": lambda: cmd_costs(args),
        "logs": lambda: cmd_logs(args),
        "export-csv": lambda: cmd_export_csv(args),
        "personas": lambda: cmd_personas(args),
        "schedule-preview": lambda: cmd_schedule_preview(args),
    }
    
    commands[args.command]()

if __name__ == "__main__":
    main()

