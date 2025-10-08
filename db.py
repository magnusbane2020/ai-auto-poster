import sqlite3
from contextlib import contextmanager
from config import CFG

@contextmanager
def get_db():
    con = sqlite3.connect(CFG["DB_PATH"])
    con.row_factory = sqlite3.Row
    try:
        yield con
    finally:
        con.commit()
        con.close()

def migrate():
    with get_db() as db:
        db.executescript("""
        CREATE TABLE IF NOT EXISTS posts(
          id INTEGER PRIMARY KEY,
          platform TEXT,
          status TEXT,
          title TEXT,
          body TEXT,
          image_path TEXT,
          scheduled_at TEXT,
          posted_at TEXT,
          permalink TEXT,
          topic_key TEXT,
          cost_usd REAL DEFAULT 0
        );
        CREATE TABLE IF NOT EXISTS topics(
          id INTEGER PRIMARY KEY,
          key TEXT UNIQUE,
          source TEXT,
          payload_json TEXT,
          discovered_at TEXT
        );
        CREATE TABLE IF NOT EXISTS ai_cache(
          id INTEGER PRIMARY KEY,
          cache_key TEXT,
          role TEXT,
          input_hash TEXT,
          output_text TEXT,
          metadata_json TEXT,
          created_at TEXT
        );
        CREATE TABLE IF NOT EXISTS logs(
          id INTEGER PRIMARY KEY,
          scope TEXT,
          level TEXT,
          message TEXT,
          meta_json TEXT,
          created_at TEXT
        );
        """)
migrate()
