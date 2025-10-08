import hashlib, json, time
from db import get_db

def _h(data: dict) -> str:
    return hashlib.sha256(json.dumps(data, sort_keys=True).encode()).hexdigest()

def get_cached(role: str, payload: dict):
    key = _h(payload)
    with get_db() as db:
        cur = db.execute("SELECT output_text, metadata_json FROM ai_cache WHERE role=? AND input_hash=? ORDER BY id DESC LIMIT 1",
                         (role, key))
        row = cur.fetchone()
        if row:
            return row["output_text"], json.loads(row["metadata_json"] or "{}")
    return None, None

def set_cached(role: str, payload: dict, output: str, meta: dict):
    key = _h(payload)
    with get_db() as db:
        db.execute("""INSERT INTO ai_cache(cache_key, role, input_hash, output_text, metadata_json, created_at)
                      VALUES(?,?,?,?,?,datetime('now'))""",
                   (key[:16], role, key, output, json.dumps(meta)))
