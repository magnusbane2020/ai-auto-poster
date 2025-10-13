"""
csv_logger.py - CSV logging for published posts.
Exports post history to /logs/posts_log.csv for analysis and tracking.
"""
import os
import csv
from datetime import datetime
from db import get_db

def ensure_logs_dir():
    """Create logs directory if it doesn't exist."""
    os.makedirs("logs", exist_ok=True)

def export_posts_to_csv(output_path: str = "logs/posts_log.csv"):
    """
    Export all posts from database to CSV file.
    Args:
        output_path: Path to CSV file
    """
    ensure_logs_dir()
    
    with get_db() as db:
        cur = db.execute("""
            SELECT 
                id, platform, status, title, scheduled_at, posted_at,
                permalink, topic_key, cost_usd, error_message, created_at
            FROM posts
            ORDER BY created_at DESC
        """)
        rows = cur.fetchall()
    
    if not rows:
        return
    
    # Write to CSV
    with open(output_path, 'w', newline='', encoding='utf-8') as f:
        fieldnames = ['id', 'platform', 'status', 'title', 'scheduled_at', 
                     'posted_at', 'permalink', 'topic_key', 'cost_usd', 
                     'error_message', 'created_at']
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        
        writer.writeheader()
        for row in rows:
            writer.writerow(dict(row))

def log_post_to_csv(post_data: dict, append_path: str = "logs/posts_log.csv"):
    """
    Append a single post to CSV log (for real-time logging).
    Args:
        post_data: Dict with post fields
        append_path: Path to CSV file
    """
    ensure_logs_dir()
    
    # Check if file exists to determine if we need header
    file_exists = os.path.exists(append_path)
    
    fieldnames = ['id', 'platform', 'status', 'title', 'scheduled_at', 
                 'posted_at', 'permalink', 'topic_key', 'cost_usd', 
                 'error_message', 'created_at']
    
    with open(append_path, 'a', newline='', encoding='utf-8') as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        
        # Write header if new file
        if not file_exists:
            writer.writeheader()
        
        writer.writerow(post_data)

def get_posting_stats() -> dict:
    """
    Get posting statistics for dashboard.
    Returns dict with counts, success rate, etc.
    """
    with get_db() as db:
        # Total posts by status
        cur = db.execute("""
            SELECT status, COUNT(*) as count, 
                   SUM(cost_usd) as total_cost
            FROM posts
            GROUP BY status
        """)
        stats = {"by_status": {row["status"]: {"count": row["count"], "cost": row["total_cost"] or 0.0} 
                               for row in cur.fetchall()}}
        
        # Posts by platform
        cur = db.execute("""
            SELECT platform, COUNT(*) as count
            FROM posts
            WHERE status='posted'
            GROUP BY platform
        """)
        stats["by_platform"] = {row["platform"]: row["count"] for row in cur.fetchall()}
        
        # Success rate
        total = sum(s["count"] for s in stats["by_status"].values())
        posted = stats["by_status"].get("posted", {}).get("count", 0)
        stats["success_rate"] = (posted / total * 100) if total > 0 else 0.0
        
        return stats

