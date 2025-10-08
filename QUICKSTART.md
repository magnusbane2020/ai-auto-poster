# 🚀 Quick Start Guide

## 1️⃣ Setup (2 minutes)

```bash
# Install dependencies
pip install -r requirements.txt

# Configure environment
cp .env.example .env
nano .env  # Add your API keys
```

## 2️⃣ Get API Credentials

### OpenAI
- Visit: https://platform.openai.com/api-keys
- Create new secret key
- Add to `.env`: `OPENAI_API_KEY=sk-...`

### Facebook Page
- Visit: https://developers.facebook.com/tools/explorer/
- Get Page ID and Page Access Token
- Add to `.env`:
  - `FB_PAGE_ID=...`
  - `FB_PAGE_ACCESS_TOKEN=...`

### LinkedIn
- Visit: https://www.linkedin.com/developers/apps
- Create app with r_liteprofile, w_member_social permissions
- Get access token
- Get your URN: `https://api.linkedin.com/v2/me` (for personal) or org URN
- Add to `.env`:
  - `LINKEDIN_ACCESS_TOKEN=...`
  - `LINKEDIN_PERSON_URN=urn:li:person:...` OR
  - `LINKEDIN_ORG_URN=urn:li:organization:...`

## 3️⃣ Run

```bash
# Option A: Run scheduler (automated daily posting)
python scheduler.py

# Option B: Use CLI commands
python app.py schedule      # Same as above
python app.py plan-now      # Generate content now
python app.py post-now      # Publish scheduled posts
python app.py status        # Check status
python app.py costs         # View costs
python app.py logs          # View logs
```

## 4️⃣ Test Before Production

```bash
# Generate content (won't publish)
python app.py plan-now

# Check what was scheduled
python app.py status

# Manually trigger publishing
python app.py post-now
```

## 5️⃣ Monitor

```bash
# View system status
python app.py status

# Check costs
python app.py costs

# View recent logs
python app.py logs --limit 50

# Direct database queries
sqlite3 posts.db "SELECT * FROM posts WHERE status='scheduled';"
```

## 📋 What Happens Automatically?

### Daily at 08:00
1. Discovers trending topics from RSS feeds
2. BMAD Supervisor selects best topic
3. Generates 3 text variants (selects best)
4. Generates AI image
5. Schedules posts for Facebook & LinkedIn (+1 hour buffer)

### Every 2 Minutes
1. Checks for scheduled posts due now
2. Publishes to platforms
3. Retries on failure (max 3 attempts)
4. Logs all activity

## 💰 Expected Costs

- **Per post**: ~$0.04-0.05 (text + image)
- **Daily**: ~$0.04-0.05 (1 post per day)
- **Monthly**: ~$1.20-1.50 (30 posts)

Costs are minimized through:
- ✅ Aggressive caching
- ✅ Batch processing
- ✅ Short prompts
- ✅ gpt-4o-mini model

## 🛠️ Configuration

Edit `.env` to customize:

```env
# Budget limits
DAILY_COST_LIMIT_USD=5.0
MONTHLY_COST_LIMIT_USD=100.0

# Timezone (affects scheduling)
TZ=Europe/Bucharest

# Brand voice
BRAND_BULLETS=Romania context,tech+educational,no fluff,clear CTA
```

Edit `scheduler.py` to customize:
- Line 214: Daily planning time (default: 08:00)
- Line 217: Posting tick interval (default: 2 minutes)

## 🐛 Troubleshooting

### "Configuration errors: OPENAI_API_KEY"
➜ Add missing keys to `.env` file

### "Rate limit exceeded"
➜ System auto-retries. If persistent, check OpenAI limits.

### "Budget limit exceeded"
➜ Increase limits in `.env` or wait for next day/month

### Posts stuck in "scheduled"
➜ Run `python app.py post-now` manually
➜ Check logs: `python app.py logs --limit 50`

## 📚 More Help

- See **README.md** for comprehensive documentation
- See **DELIVERY_SUMMARY.md** for technical details
- Check code comments for inline documentation

## 🎯 Production Checklist

- [ ] API keys added to `.env`
- [ ] Test run: `python app.py plan-now`
- [ ] Check scheduled posts: `python app.py status`
- [ ] Manual publish test: `python app.py post-now`
- [ ] Monitor logs: `python app.py logs`
- [ ] Set up process manager (systemd, supervisor, PM2)
- [ ] Configure alerts (optional)
- [ ] Schedule regular backups of `posts.db`

---

**You're ready to go! 🎉**

Run `python scheduler.py` and the system will automatically:
1. Discover trending topics daily
2. Generate engaging content
3. Schedule posts with review buffer
4. Publish to Facebook & LinkedIn
5. Track costs and logs
