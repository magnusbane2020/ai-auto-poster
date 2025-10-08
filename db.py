"""
db.py - SQLite database connection and schema management
Provides context manager for safe DB operations with automatic commit/rollback.
Schema: posts, topics, ai_cache, logs tables for complete workflow tracking.
"""
import sqlite3
import json
from contextlib import contextmanager
from typing import Generator, Any
from datetime import datetime
from dotenv import load_dotenv

# Load environment variables before importing config
load_dotenv()
from config import CFG


@contextmanager
def get_db() -> Generator[sqlite3.Connection, None, None]:
    """
    Context manager for database connections.
    Auto-commits on success, rollback on exception.
    """
    con = sqlite3.connect(CFG["DB_PATH"])
    con.row_factory = sqlite3.Row
    try:
        yield con
        con.commit()
    except Exception as e:
        con.rollback()
        raise
    finally:
        con.close()


def migrate() -> None:
    """Initialize database schema. Idempotent - safe to run multiple times."""
    with get_db() as db:
        db.executescript("""
        -- Posts table: tracks all generated and published posts
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
          retry_count INTEGER DEFAULT 0,
          error_message TEXT,
          created_at TEXT DEFAULT (datetime('now'))
        );
        CREATE INDEX IF NOT EXISTS idx_posts_status ON posts(status, scheduled_at);
        CREATE INDEX IF NOT EXISTS idx_posts_platform ON posts(platform);
        
        -- Topics table: stores discovered trending topics
        CREATE TABLE IF NOT EXISTS topics(
          id INTEGER PRIMARY KEY AUTOINCREMENT,
          key TEXT UNIQUE NOT NULL,
          source TEXT NOT NULL,
          title TEXT,
          payload_json TEXT,
          discovered_at TEXT DEFAULT (datetime('now'))
        );
        CREATE INDEX IF NOT EXISTS idx_topics_key ON topics(key);
        
        -- AI Cache table: prevents duplicate API calls, saves costs
        CREATE TABLE IF NOT EXISTS ai_cache(
          id INTEGER PRIMARY KEY AUTOINCREMENT,
          cache_key TEXT NOT NULL,
          role TEXT NOT NULL,
          input_hash TEXT UNIQUE NOT NULL,
          output_text TEXT NOT NULL,
          metadata_json TEXT,
          created_at TEXT DEFAULT (datetime('now'))
        );
        CREATE INDEX IF NOT EXISTS idx_cache_lookup ON ai_cache(role, input_hash);
        
        -- Logs table: detailed error and activity tracking
        CREATE TABLE IF NOT EXISTS logs(
          id INTEGER PRIMARY KEY AUTOINCREMENT,
          scope TEXT NOT NULL,
          level TEXT NOT NULL,
          message TEXT NOT NULL,
          meta_json TEXT,
          created_at TEXT DEFAULT (datetime('now'))
        );
        CREATE INDEX IF NOT EXISTS idx_logs_scope ON logs(scope, created_at);
        """)


def log_event(scope: str, level: str, message: str, meta: dict[str, Any] | None = None) -> None:
    """
    Log an event to the database.
    
    Args:
        scope: Module/function name (e.g., 'scheduler.plan_daily')
        level: INFO, WARNING, ERROR
        message: Human-readable message
        meta: Additional context data
    """
    with get_db() as db:
        db.execute(
            "INSERT INTO logs(scope, level, message, meta_json) VALUES(?,?,?,?)",
            (scope, level, message, json.dumps(meta or {}))
        )


def store_topic(key: str, source: str, title: str, payload: dict[str, Any]) -> None:
    """Store a discovered topic (idempotent via UNIQUE constraint)."""
    with get_db() as db:
        try:
            db.execute(
                "INSERT OR IGNORE INTO topics(key, source, title, payload_json) VALUES(?,?,?,?)",
                (key, source, title, json.dumps(payload))
            )
        except sqlite3.IntegrityError:
            pass  # Already exists, that's fine


# Run migrations on import
migrate()

