"""
db.py - SQLite database layer with context manager and migrations.
Stores posts, topics, AI cache, cost tracking, and logs.
Auto-migrates on import. Idempotent schema creation.
"""
import sqlite3
import json
from contextlib import contextmanager
from datetime import datetime
from dotenv import load_dotenv

# Memory requirement: load dotenv before importing config
load_dotenv()

from config import CFG

@contextmanager
def get_db():
    """Context manager for SQLite connection with auto-commit."""
    con = sqlite3.connect(CFG["DB_PATH"])
    con.row_factory = sqlite3.Row
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
<<<<<<< Current (Your changes)
=======

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

# Auto-migrate on import
>>>>>>> Incoming (Background Agent changes)
migrate()
