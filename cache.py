"""
cache.py - AI response caching to minimize API costs
Caches OpenAI responses by input hash. Saves significant money on repeated queries.
Cache hit = $0 cost. Use aggressively for production cost optimization.
"""
import hashlib
import json
from typing import Any, Tuple, Optional
from db import get_db, log_event


def _hash_payload(data: dict[str, Any]) -> str:
    """Generate deterministic hash from input payload."""
    return hashlib.sha256(json.dumps(data, sort_keys=True).encode()).hexdigest()


def get_cached(role: str, payload: dict[str, Any]) -> Tuple[Optional[str], Optional[dict]]:
    """
    Retrieve cached AI response if exists.
    
    Args:
        role: Cache namespace (e.g., 'text_v1', 'img_v1')
        payload: Input parameters to hash
    
    Returns:
        (output_text, metadata) or (None, None) if cache miss
    """
    input_hash = _hash_payload(payload)
    
    with get_db() as db:
        cur = db.execute(
            "SELECT output_text, metadata_json FROM ai_cache WHERE role=? AND input_hash=? ORDER BY id DESC LIMIT 1",
            (role, input_hash)
        )
        row = cur.fetchone()
        
        if row:
            log_event("cache", "INFO", f"Cache HIT for role={role}", {"hash": input_hash[:12]})
            return row["output_text"], json.loads(row["metadata_json"] or "{}")
    
    log_event("cache", "INFO", f"Cache MISS for role={role}", {"hash": input_hash[:12]})
    return None, None


def set_cached(role: str, payload: dict[str, Any], output: str, meta: dict[str, Any]) -> None:
    """
    Store AI response in cache.
    
    Args:
        role: Cache namespace
        payload: Input parameters
        output: AI response to cache
        meta: Additional metadata (tokens used, cost, etc.)
    """
    input_hash = _hash_payload(payload)
    cache_key = input_hash[:16]  # Short prefix for quick reference
    
    with get_db() as db:
        try:
            db.execute(
                """INSERT OR REPLACE INTO ai_cache(cache_key, role, input_hash, output_text, metadata_json)
                   VALUES(?,?,?,?,?)""",
                (cache_key, role, input_hash, output, json.dumps(meta))
            )
            log_event("cache", "INFO", f"Cache SET for role={role}", {"hash": input_hash[:12]})
        except Exception as e:
            log_event("cache", "ERROR", f"Failed to cache: {e}", {"role": role})


def clear_cache(role: Optional[str] = None, older_than_days: Optional[int] = None) -> int:
    """
    Clear cache entries. Useful for testing or managing storage.
    
    Args:
        role: If specified, only clear this role's cache
        older_than_days: If specified, only clear entries older than N days
    
    Returns:
        Number of entries deleted
    """
    with get_db() as db:
        if role and older_than_days:
            result = db.execute(
                "DELETE FROM ai_cache WHERE role=? AND created_at < datetime('now', ? || ' days')",
                (role, f"-{older_than_days}")
            )
        elif role:
            result = db.execute("DELETE FROM ai_cache WHERE role=?", (role,))
        elif older_than_days:
            result = db.execute(
                "DELETE FROM ai_cache WHERE created_at < datetime('now', ? || ' days')",
                (f"-{older_than_days}",)
            )
        else:
            result = db.execute("DELETE FROM ai_cache")
        
        deleted = result.rowcount
        log_event("cache", "WARNING", f"Cleared {deleted} cache entries", {"role": role, "days": older_than_days})
        return deleted

