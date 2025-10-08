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
from datetime import datetime, timezone

from config import CFG, validate_config
from db import get_db, log_event
from scheduler import plan_daily, tick, run_scheduler

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
        today = datetime.now(timezone.utc).strftime("%Y-%m-%d")
        cur = db.execute("SELECT SUM(cost_usd) as total FROM costs WHERE date=?", (today,))
        daily_cost = cur.fetchone()["total"] or 0.0
        
        # Month's costs
        month_start = datetime.now(timezone.utc).replace(day=1).strftime("%Y-%m-%d")
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
    }
    
    commands[args.command]()

if __name__ == "__main__":
    main()
