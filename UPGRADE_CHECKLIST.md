# ✅ ai-auto-poster v2.3 Upgrade Checklist

**Ready to upgrade? Follow this checklist step by step!**

---

## 📋 Pre-Upgrade Checklist

- [ ] **Backup your current database**
  ```bash
  cp posts.db posts.db.backup
  ```

- [ ] **Note your current .env settings**
  ```bash
  cat .env > env.backup
  ```

- [ ] **Check Python version**
  ```bash
  python --version  # Should be 3.9+
  ```

- [ ] **Verify git status**
  ```bash
  git status  # Commit or stash changes
  ```

---

## 🚀 Installation Steps

### Step 1: Update Code ✅

- [ ] **Pull latest changes**
  ```bash
  git pull origin main
  ```
  
- [ ] **Verify files updated**
  - [ ] `db.py` - Enhanced reliability
  - [ ] `config.py` - Canva settings
  - [ ] `ai_agent.py` - Hybrid images
  - [ ] `requirements.txt` - Dependencies

- [ ] **Verify new files created**
  - [ ] `canva_client.py` - Canva integration
  - [ ] `db_monitor.py` - Monitoring system
  - [ ] `DB_CANVA_INTEGRATION_GUIDE.md`
  - [ ] `QUICK_REFERENCE.md`
  - [ ] `ENVIRONMENT_SETUP.md`
  - [ ] `RELEASE_NOTES_v2.3.md`

### Step 2: Update Dependencies ✅

- [ ] **Install/update packages**
  ```bash
  pip install --upgrade -r requirements.txt
  ```

- [ ] **Verify installation**
  ```bash
  pip list | grep -E "openai|httpx|apscheduler"
  ```

### Step 3: Configure Environment (Optional) ✅

**If using Canva (optional):**

- [ ] **Add Canva settings to .env**
  ```bash
  USE_CANVA=true
  CANVA_API_KEY=your-api-key-here
  CANVA_TEAM_ID=your-team-id
  CANVA_BRAND_TEMPLATE_ID=your-template-id
  ```

**If NOT using Canva:**

- [ ] **Ensure DALL-E fallback enabled**
  ```bash
  USE_CANVA=false  # or omit entirely
  ```

### Step 4: Test Database Health ✅

- [ ] **Run health check**
  ```bash
  python db_monitor.py
  ```

- [ ] **Expected output:**
  ```
  ✅ Database file: posts.db (X.XX MB)
  ✅ Lock file: posts.db-wal (clear)
  ✅ Journal mode: wal
  ✅ Integrity: OK
  ✅ DATABASE HEALTHY
  ```

- [ ] **If issues found, run self-heal**
  ```bash
  python db_monitor.py  # Auto-heals
  ```

### Step 5: Test Image Generation ✅

**Test DALL-E (always available):**

- [ ] **Generate test image**
  ```bash
  python -c "from ai_agent import generate_image; img = generate_image('Test AI dashboard', save_path='media/test_dalle.png', prefer_canva=False); print(f'✅ Generated {len(img)} bytes')"
  ```

- [ ] **Verify image created**
  ```bash
  ls -lh media/test_dalle.png
  ```

**Test Canva (if enabled):**

- [ ] **Generate test image**
  ```bash
  python -c "from canva_client import generate_canva_image; img, src = generate_canva_image('Test brand post', 'media/test_canva.png'); print(f'✅ Source: {src}')"
  ```

- [ ] **Expected output:**
  ```
  ✅ Source: canva
  # OR
  ⚠️ Source: disabled  # If Canva not enabled
  # OR
  ⚠️ Source: error  # Falls back to DALL-E
  ```

### Step 6: Verify Configuration ✅

- [ ] **Check config validation**
  ```bash
  python -c "from config import validate_config; errors = validate_config(); print('✅ Config valid!' if not errors else f'❌ Missing: {errors}')"
  ```

- [ ] **Review settings**
  ```bash
  python -c "from config import CFG; print('Canva enabled:', CFG['USE_CANVA']); print('DB path:', CFG['DB_PATH'])"
  ```

### Step 7: Test Full System ✅

- [ ] **Start application**
  ```bash
  python app.py
  ```

- [ ] **Visit web interface**
  ```
  http://localhost:5000
  ```

- [ ] **Check console output**
  ```
  ⚙️ [HH:MM:SS] SQLite connection active (attempt 1)
  ✅ Database healthy
  * Running on http://127.0.0.1:5000
  ```

- [ ] **Test concurrent access (optional)**
  - Keep app running
  - Open new terminal
  - Run: `python -c "from db import monitor_db; monitor_db()"`
  - Should succeed without "database is locked" ❌

---

## 🧪 Post-Upgrade Verification

### Functional Tests ✅

- [ ] **Database operations work**
  ```bash
  python -c "from db import get_db; 
  with get_db() as db: 
      cursor = db.execute('SELECT COUNT(*) FROM posts'); 
      print(f'✅ Posts: {cursor.fetchone()[0]}')"
  ```

- [ ] **Image generation works**
  ```bash
  python -c "from ai_agent import generate_image; 
  img = generate_image('AI automation', save_path='media/verify.png'); 
  print(f'✅ Image: {len(img)} bytes')"
  ```

- [ ] **Monitoring works**
  ```bash
  python -c "from db_monitor import get_db_metrics; 
  import json; 
  print(json.dumps(get_db_metrics(), indent=2))"
  ```

- [ ] **Self-healing works**
  ```bash
  python -c "from db_monitor import heal_database; 
  report = heal_database(verbose=False); 
  print(f'✅ Actions: {len(report[\"actions\"])}')"
  ```

### Performance Tests ✅

- [ ] **No database locks**
  - [ ] Run app
  - [ ] Run `python db_monitor.py` (concurrent)
  - [ ] Should succeed immediately

- [ ] **Image generation speed**
  - [ ] DALL-E: ~3-5 seconds
  - [ ] Canva: ~5-10 seconds (if enabled)

- [ ] **Database health check**
  - [ ] Should complete in < 2 seconds

### Log Verification ✅

- [ ] **Check for errors**
  ```bash
  # No critical errors expected
  grep -i "error\|failed" logs/*.csv | tail -20
  ```

- [ ] **Verify new log entries**
  ```bash
  # Should see db_monitor and canva_client entries
  grep "db_monitor\|canva_client" logs/*.csv | tail -10
  ```

---

## 📊 Success Criteria

### ✅ Must Have (Required)

- [ ] Database health check passes
- [ ] No "database is locked" errors
- [ ] Image generation works (DALL-E minimum)
- [ ] App starts without errors
- [ ] Config validation passes

### 🎯 Nice to Have (Optional)

- [ ] Canva integration working
- [ ] Self-healing tested
- [ ] Concurrent access tested
- [ ] Performance improved
- [ ] Logs clean and informative

---

## 🚨 Troubleshooting

### Issue: Database locked (shouldn't happen!)

**Quick fix:**
```bash
python db_monitor.py  # Auto-heals
```

**Manual fix:**
```bash
rm posts.db-wal posts.db-shm
python -c "from db import checkpoint_wal; checkpoint_wal()"
```

### Issue: Canva not working

**Check config:**
```bash
python -c "from config import CFG; print('Enabled:', CFG['USE_CANVA']); print('Key set:', bool(CFG['CANVA_API_KEY']))"
```

**Disable if needed:**
```bash
# In .env
USE_CANVA=false
```

**Expected:** System falls back to DALL-E automatically ✅

### Issue: Import errors

**Reinstall dependencies:**
```bash
pip install --force-reinstall -r requirements.txt
```

**Check Python version:**
```bash
python --version  # Should be 3.9+
```

### Issue: Missing .env

**Create from template:**
```bash
cp ENVIRONMENT_SETUP.md .env
# Edit .env with your credentials
```

---

## 📚 Documentation Quick Links

- **Complete Guide:** `DB_CANVA_INTEGRATION_GUIDE.md` (800 lines)
- **Quick Reference:** `QUICK_REFERENCE.md` (200 lines)
- **Setup Guide:** `ENVIRONMENT_SETUP.md` (150 lines)
- **Release Notes:** `RELEASE_NOTES_v2.3.md` (250 lines)
- **Implementation:** `IMPLEMENTATION_SUMMARY.md` (this sprint)

---

## 🎯 Next Steps After Upgrade

### Immediate (First 24 Hours)

- [ ] **Monitor logs closely**
  ```bash
  tail -f logs/*.csv
  ```

- [ ] **Test image generation 5+ times**
  - [ ] Both Canva and DALL-E (if applicable)
  - [ ] Verify quality and consistency

- [ ] **Run health check 3+ times**
  - [ ] Morning, afternoon, evening
  - [ ] Ensure stability

### Short-term (First Week)

- [ ] **Schedule weekly health checks**
  - [ ] Every Monday: `python db_monitor.py`
  - [ ] Or add to cron/scheduler

- [ ] **Track cost trends**
  ```bash
  python -c "from db import get_db; 
  with get_db() as db:
      cursor = db.execute('SELECT SUM(cost_usd) FROM costs WHERE date >= date(\"now\", \"-7 days\")');
      print(f'Weekly cost: ${cursor.fetchone()[0]:.2f}')"
  ```

- [ ] **Optimize Canva templates** (if using)
  - [ ] Test different designs
  - [ ] Measure engagement

### Long-term (First Month)

- [ ] **Review performance metrics**
  - [ ] Uptime: Should be 99.9%
  - [ ] Lock errors: Should be 0
  - [ ] Image quality: Consistent

- [ ] **Consider automation enhancements**
  - [ ] Webhook alerts
  - [ ] Grafana dashboard
  - [ ] A/B testing

---

## ✅ Final Checklist

**Before marking complete, verify:**

- [ ] All code updated (4 files modified, 6 files created)
- [ ] Dependencies installed
- [ ] .env configured (Canva optional)
- [ ] Database health check passes
- [ ] Image generation works
- [ ] App runs without errors
- [ ] No linting errors
- [ ] Documentation reviewed
- [ ] 24-hour monitoring planned

---

## 🎉 Congratulations!

If all checkboxes above are ✅, you've successfully upgraded to v2.3!

**What you now have:**
- ✅ Bulletproof database (zero locks)
- ✅ Professional images (Canva + DALL-E)
- ✅ Self-healing system
- ✅ Comprehensive monitoring
- ✅ Production-ready automation

**Go automate those social posts with confidence!** 🚀

---

**Version:** 2.3.0  
**Status:** Upgrade Complete ✅  
**Date:** October 12, 2025

---

*For questions or issues:*
1. *Check `DB_CANVA_INTEGRATION_GUIDE.md` for detailed help*
2. *Run `python db_monitor.py` for diagnostics*
3. *Review logs in `logs/` directory*

