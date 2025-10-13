# 🚀 Quick Reference Card - ai-auto-poster v2.3

## 🏃 Quick Start

### 1. Check Database Health
```bash
python db_monitor.py
```

### 2. Run App
```bash
python app.py
```

### 3. Test Image Generation
```python
from ai_agent import generate_image
img = generate_image("AI dashboard", save_path="media/test.png")
print(f"Generated {len(img)} bytes")
```

---

## 📦 Core Commands

### Database Operations
```python
from db import monitor_db, checkpoint_wal, get_connection

# Check health
monitor_db()

# Force checkpoint
checkpoint_wal()

# Get connection (bulletproof)
conn = get_connection(retries=5)
```

### Monitoring & Healing
```python
from db_monitor import monitor_database, heal_database

# Health check
health = monitor_database(verbose=True)

# Self-heal
report = heal_database(verbose=True)

# Get metrics
from db_monitor import get_db_metrics
metrics = get_db_metrics()
```

### Image Generation
```python
from ai_agent import generate_image

# Tries Canva first, falls back to DALL-E
image = generate_image(
    prompt="Professional AI post",
    size="1024x1024",
    save_path="media/post.png",
    prefer_canva=True  # Default
)
```

### Canva Direct
```python
from canva_client import generate_canva_image

image_data, source = generate_canva_image(
    prompt="Branded social post",
    save_path="media/canva_post.png"
)

# source = "canva", "disabled", "error", "create_failed", etc.
```

---

## 🔧 Configuration

### Environment Variables (.env)
```bash
# Required
OPENAI_API_KEY=sk-...
FB_PAGE_ID=...
FB_PAGE_ACCESS_TOKEN=...
LINKEDIN_ACCESS_TOKEN=...
LINKEDIN_PERSON_URN=...  # OR LINKEDIN_ORG_URN

# Optional - Canva
USE_CANVA=true
CANVA_API_KEY=...
CANVA_TEAM_ID=...
CANVA_BRAND_TEMPLATE_ID=...

# Budget
DAILY_COST_LIMIT_USD=5.0
MONTHLY_COST_LIMIT_USD=100.0
```

---

## 🩺 Troubleshooting

### "Database is locked"
```python
from db_monitor import heal_database
heal_database()
```

### Check Canva status
```python
from config import CFG
print("Canva enabled:", CFG["USE_CANVA"])
print("API key set:", bool(CFG["CANVA_API_KEY"]))
```

### Force DALL-E only
```python
from ai_agent import generate_image
img = generate_image(prompt="...", prefer_canva=False)
```

### Clean stale locks manually
```bash
rm posts.db-wal posts.db-shm
python -c "from db import checkpoint_wal; checkpoint_wal()"
```

---

## 📊 Health Check Output

### Good ✅
```
✅ Database file: posts.db (0.45 MB)
✅ Lock file: posts.db-wal (clear)
✅ Journal mode: wal
✅ Integrity: OK
✅ DATABASE HEALTHY
```

### Warning ⚠️
```
⚠️ Lock file: posts.db-wal (32.5 KB)
⚠️ 3 posts scheduled over 7 days ago
⚠️ DATABASE OK - 2 warnings
```

### Error ❌
```
❌ Database connection: FAILED
❌ DATABASE UNHEALTHY
```
**Fix:** Run `python db_monitor.py` for auto-healing

---

## 🎨 Image Generation Flow

```
generate_image(prompt)
    ↓
[USE_CANVA=true?]
    ↓
YES → Try Canva
    ├─ Success ✅ → Return image
    └─ Fail ⚠️ → Fall back to DALL-E
NO → Use DALL-E
    ├─ Check text (OCR)
    ├─ Retry if text found
    └─ Return image
```

---

## 🔑 Key Files

| File | Purpose |
|------|---------|
| `db.py` | Database layer (WAL, retry, monitoring) |
| `db_monitor.py` | Health check & self-healing |
| `canva_client.py` | Canva API integration |
| `ai_agent.py` | AI content generation (text + images) |
| `config.py` | Configuration loader |
| `app.py` | Flask web app |
| `scheduler.py` | Automated posting schedule |

---

## 🚨 Common Issues

### 1. Database locked
**Fix:** Already handled automatically! System retries 5 times.

### 2. Canva not working
**Fix:** Check logs, system falls back to DALL-E automatically.

### 3. Large cache
**Fix:** Run `python db_monitor.py` - auto-prunes old entries.

### 4. Fragmentation
**Fix:** Run `python db_monitor.py` - runs VACUUM if needed.

---

## 📈 Performance Tips

1. **Let it auto-heal** - Run `db_monitor.py` daily
2. **Use Canva for brand** - Better quality, more consistent
3. **Monitor logs** - Check for patterns in issues
4. **Keep cache under 5K** - Auto-pruned by monitor
5. **Checkpoint WAL daily** - Already automatic on exit

---

## 🎯 Testing Checklist

- [ ] Database health: `python db_monitor.py`
- [ ] Canva works: Test with `generate_canva_image()`
- [ ] DALL-E fallback: Set `USE_CANVA=false`, test
- [ ] Concurrent access: Run app + manual script
- [ ] Self-healing: Create stale lock, run monitor
- [ ] Image quality: Generate 5 images, check all

---

## 📞 Quick Diagnostics

### Check everything at once:
```bash
python -c "
from db_monitor import monitor_database, get_db_metrics
from config import CFG

print('=== DATABASE ===')
monitor_database()

print('\n=== METRICS ===')
import json
print(json.dumps(get_db_metrics(), indent=2))

print('\n=== CONFIG ===')
print('Canva enabled:', CFG['USE_CANVA'])
print('DB path:', CFG['DB_PATH'])
"
```

---

## 🎓 Learn More

- **Full Guide:** `DB_CANVA_INTEGRATION_GUIDE.md`
- **Architecture:** `ARCHITECTURE_STATUS.md`
- **Release Notes:** `RELEASE_NOTES_v2.2.md`

---

**Version:** 2.3  
**Last Updated:** October 12, 2025  
**Status:** Production Ready ✅

