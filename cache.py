"""
cache.py - AI response caching to minimize duplicate API calls.
Uses SQLite table ai_cache with hash-based lookup.
Significantly reduces costs for repeated queries.
"""
import hashlib
import json
from db import get_db

def _h(data: dict) -> str:
    """Generate deterministic hash from dict payload."""
    return hashlib.sha256(json.dumps(data, sort_keys=True).encode()).hexdigest()

def get_cached(role: str, payload: dict) -> tuple[str | None, dict | None]:
    """
    Retrieve cached AI response.
    Args:
        role: Cache namespace (e.g. 'text_v1', 'img_v1')
        payload: Input dict to hash
    Returns:
        (output_text, metadata_dict) or (None, None) if not cached
    """
    key = _h(payload)
    with get_db() as db:
        cur = db.execute(
            "SELECT output_text, metadata_json FROM ai_cache WHERE role=? AND input_hash=? ORDER BY id DESC LIMIT 1",
            (role, key)
        )
        row = cur.fetchone()
        if row:
            return row["output_text"], json.loads(row["metadata_json"] or "{}")
    return None, None

def set_cached(role: str, payload: dict, output: str, meta: dict):
    """
    Store AI response in cache.
    Args:
        role: Cache namespace
        payload: Input dict (will be hashed)
        output: AI response text
        meta: Metadata dict (tokens, cost, etc.)
    """
    key = _h(payload)
    with get_db() as db:
<<<<<<< Current (Your changes)
        db.execute("""INSERT INTO ai_cache(cache_key, role, input_hash, output_text, metadata_json, created_at)
                      VALUES(?,?,?,?,?,datetime('now'))""",
                   (key[:16], role, key, output, json.dumps(meta)))
=======
        db.execute(
            """INSERT INTO ai_cache(cache_key, role, input_hash, output_text, metadata_json)
               VALUES(?,?,?,?,?)""",
            (key[:16], role, key, output, json.dumps(meta))
        )

def clear_old_cache(days: int = 30):
    """Clean up cache entries older than N days. TODO: Add to maintenance cron."""
    with get_db() as db:
        db.execute(
            "DELETE FROM ai_cache WHERE created_at < datetime('now', ?)",
            (f"-{days} days",)
        )
>>>>>>> Incoming (Background Agent changes)
