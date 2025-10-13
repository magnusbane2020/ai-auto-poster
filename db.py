"""
db.py - SQLite database layer with context manager and migrations.
Stores posts, topics, AI cache, cost tracking, and logs.
Auto-migrates on import. Idempotent schema creation.
Enhanced with bulletproof WAL mode, retry logic, cleanup, and monitoring.
"""
import sqlite3
import json
import time
import os
import atexit
from contextlib import contextmanager
from datetime import datetime
from dotenv import load_dotenv

# Memory requirement: load dotenv before importing config
load_dotenv()

from config import CFG

LOCK_FILES = ["posts.db-wal", "posts.db-shm"]

def _cleanup_locks():
    """Remove leftover SQLite WAL/SHM locks if they exist."""
    for f in LOCK_FILES:
        if os.path.exists(f):
            try:
                os.remove(f)
                print(f"🧹 [{datetime.now().strftime('%H:%M:%S')}] Removed stale lock file: {f}")
            except Exception as e:
                # File might be in use - that's OK, continue
                pass

def get_connection(retries=5, delay=1):
    """
    Create a fault-tolerant SQLite connection with:
    - WAL mode (safe concurrent writes)
    - Retry logic if locked
    - Auto-cleanup for stale files
    - Enhanced busy timeout and synchronization
    
    Args:
        retries: Number of retry attempts
        delay: Delay between retries in seconds
    Returns:
        SQLite connection with WAL mode enabled
    """
    db_path = CFG["DB_PATH"]
    
    # Clean up any stale lock files first
    _cleanup_locks()
    
    # Attempt multiple retries before giving up
    for attempt in range(retries):
        try:
            conn = sqlite3.connect(db_path, timeout=10, isolation_level=None)
            conn.row_factory = sqlite3.Row
            
            # Enable WAL mode for concurrent-safe operations
            conn.execute("PRAGMA journal_mode=WAL;")
            
            # Enhanced busy timeout (5 seconds)
            conn.execute("PRAGMA busy_timeout = 5000;")
            
            # Optimize for reliability over speed
            conn.execute("PRAGMA synchronous = NORMAL;")
            
            # Better cache for read performance
            conn.execute("PRAGMA cache_size = -64000;")  # 64MB cache
            
            print(f"⚙️ [{datetime.now().strftime('%H:%M:%S')}] SQLite connection active (attempt {attempt+1})")
            
            return conn
        except sqlite3.OperationalError as e:
            if "database is locked" in str(e).lower():
                print(f"⏳ Database locked, retrying ({attempt + 1}/{retries})...")
                time.sleep(delay)
            else:
                raise
    
    raise Exception("❌ Could not access database after multiple retries.")

@contextmanager
def get_db():
    """
    Context manager for SQLite connection with auto-commit.
    Uses robust connection factory with retry logic and crash recovery.
    """
    con = get_connection()
    
    try:
        yield con
    finally:
        con.commit()
        con.close()

def migrate():
    """Idempotent schema migrations. Safe to run multiple times."""
    with get_db() as db:
        db.executescript("""
        CREATE TABLE IF NOT EXISTS posts(
          id INTEGER PRIMARY KEY AUTOINCREMENT,
          platform TEXT NOT NULL,
          status TEXT NOT NULL DEFAULT 'scheduled',
          title TEXT,
          body TEXT NOT NULL,
          image_path TEXT,
          scheduled_at TEXT NOT NULL,
          posted_at TEXT,
          permalink TEXT,
          topic_key TEXT,
          cost_usd REAL DEFAULT 0,
          error_message TEXT,
          retry_count INTEGER DEFAULT 0,
          created_at TEXT DEFAULT (datetime('now'))
        );
        CREATE INDEX IF NOT EXISTS idx_posts_status ON posts(status, scheduled_at);
        
        CREATE TABLE IF NOT EXISTS topics(
          id INTEGER PRIMARY KEY AUTOINCREMENT,
          key TEXT UNIQUE NOT NULL,
          source TEXT,
          payload_json TEXT,
          discovered_at TEXT DEFAULT (datetime('now'))
        );
        
        CREATE TABLE IF NOT EXISTS ai_cache(
          id INTEGER PRIMARY KEY AUTOINCREMENT,
          cache_key TEXT,
          role TEXT NOT NULL,
          input_hash TEXT NOT NULL,
          output_text TEXT,
          metadata_json TEXT,
          created_at TEXT DEFAULT (datetime('now'))
        );
        CREATE INDEX IF NOT EXISTS idx_cache_lookup ON ai_cache(role, input_hash);
        
        CREATE TABLE IF NOT EXISTS logs(
          id INTEGER PRIMARY KEY AUTOINCREMENT,
          scope TEXT NOT NULL,
          level TEXT NOT NULL,
          message TEXT NOT NULL,
          meta_json TEXT,
          created_at TEXT DEFAULT (datetime('now'))
        );
        CREATE INDEX IF NOT EXISTS idx_logs_scope ON logs(scope, created_at);
        
        CREATE TABLE IF NOT EXISTS costs(
          id INTEGER PRIMARY KEY AUTOINCREMENT,
          date TEXT NOT NULL,
          scope TEXT NOT NULL,
          model TEXT,
          tokens INTEGER,
          cost_usd REAL NOT NULL,
          metadata_json TEXT,
          created_at TEXT DEFAULT (datetime('now'))
        );
        CREATE INDEX IF NOT EXISTS idx_costs_date ON costs(date);
        """)

def log_event(scope: str, level: str, message: str, meta: dict = None):
    """Insert structured log entry."""
    with get_db() as db:
        db.execute(
            "INSERT INTO logs(scope, level, message, meta_json) VALUES(?,?,?,?)",
            (scope, level, message, json.dumps(meta or {}))
        )

def record_cost(scope: str, model: str, tokens: int, cost_usd: float, meta: dict = None):
    """Record API cost for tracking and limits."""
    date = datetime.utcnow().strftime("%Y-%m-%d")
    with get_db() as db:
        db.execute(
            "INSERT INTO costs(date, scope, model, tokens, cost_usd, metadata_json) VALUES(?,?,?,?,?,?)",
            (date, scope, model, tokens, cost_usd, json.dumps(meta or {}))
        )

def monitor_db():
    """Diagnostic function to print DB status and open connections."""
    print("🔍 Database monitor active...")
    db_path = CFG["DB_PATH"]
    
    # Check if database file exists
    if os.path.exists(db_path):
        size_mb = os.path.getsize(db_path) / (1024 * 1024)
        print(f"  Database: {db_path} ({size_mb:.2f} MB)")
    else:
        print(f"  Database: {db_path} (NOT FOUND)")
    
    # Check lock files
    for f in LOCK_FILES:
        exists = os.path.exists(f)
        status = "EXISTS" if exists else "ok"
        if exists:
            size_kb = os.path.getsize(f) / 1024
            print(f"  {f}: {status} ({size_kb:.2f} KB)")
        else:
            print(f"  {f}: {status}")
    
    # Try to connect and check WAL mode
    try:
        conn = get_connection()
        cursor = conn.execute("PRAGMA journal_mode;")
        mode = cursor.fetchone()[0]
        print(f"  Journal mode: {mode}")
        
        # Check table counts
        cursor = conn.execute("SELECT COUNT(*) FROM posts")
        posts_count = cursor.fetchone()[0]
        print(f"  Posts: {posts_count}")
        
        cursor = conn.execute("SELECT COUNT(*) FROM topics")
        topics_count = cursor.fetchone()[0]
        print(f"  Topics: {topics_count}")
        
        cursor = conn.execute("SELECT COUNT(*) FROM ai_cache")
        cache_count = cursor.fetchone()[0]
        print(f"  AI Cache: {cache_count}")
        
        conn.close()
        print("✅ Database healthy")
    except Exception as e:
        print(f"❌ Database error: {e}")

def checkpoint_wal():
    """Force WAL checkpoint to merge changes into main DB file."""
    try:
        conn = get_connection()
        conn.execute("PRAGMA wal_checkpoint(TRUNCATE);")
        conn.close()
        print(f"✅ [{datetime.now().strftime('%H:%M:%S')}] WAL checkpoint completed")
    except Exception as e:
        print(f"⚠️ WAL checkpoint failed: {e}")

# Register cleanup on exit
atexit.register(_cleanup_locks)
atexit.register(checkpoint_wal)

# Auto-migrate on import
migrate()
