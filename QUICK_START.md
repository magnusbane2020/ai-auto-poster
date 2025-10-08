# AI Auto-Poster - Quick Start Guide

## ⚡ 5-Minute Setup

### Step 1: Install (1 minute)
```bash
pip install -r requirements.txt
```

### Step 2: Configure (2 minutes)
```bash
cp .env.example .env
nano .env  # Add your API keys
```

Required variables:
```bash
OPENAI_API_KEY=sk-...
FB_PAGE_ID=123456789
FB_PAGE_ACCESS_TOKEN=...
LINKEDIN_ACCESS_TOKEN=...
LINKEDIN_PERSON_URN=urn:li:person:...
```

### Step 3: Validate (1 minute)
```bash
python scheduler.py --validate
```

Expected: ✅ for Facebook and LinkedIn

### Step 4: Test (1 minute)
```bash
python scheduler.py --plan-now
```

This generates content and schedules posts.

### Step 5: Run
```bash
python scheduler.py
```

Done! 🎉

---

## 📋 Common Commands

### Testing
```bash
python app.py test-all        # Test everything
python app.py test-config     # Check credentials
python app.py test-trends     # Test RSS feeds
python app.py test-ai         # Test OpenAI
```

### Operations
```bash
python scheduler.py           # Start scheduler
python scheduler.py --plan-now   # Generate content now
python scheduler.py --post-now   # Publish now
python scheduler.py --validate   # Check setup
```

### Monitoring
```bash
python app.py stats           # System statistics
python app.py posts           # Recent posts
```

---

## 🔍 Troubleshooting

### "ModuleNotFoundError: No module named 'dotenv'"
```bash
pip install -r requirements.txt
```

### "Configuration errors: Missing OPENAI_API_KEY"
```bash
# Check .env exists
ls -la .env

# Check contents
cat .env | grep OPENAI_API_KEY
```

### "Facebook credentials invalid"
- Regenerate token at developers.facebook.com
- Ensure permissions: `pages_manage_posts`, `pages_read_engagement`

### "LinkedIn posting failed"
- LinkedIn tokens expire after 60 days
- Regenerate at linkedin.com/developers

---

## 📊 File Structure

```
ai-auto-poster/
├── scheduler.py          ⭐ Main entry point
├── app.py               🧪 Testing utilities
├── config.py            ⚙️  Configuration
├── db.py                💾 Database
├── cache.py             💰 Cost optimization
├── guardrails.py        🛡️  Content validation
├── ai_agent.py          🤖 OpenAI integration
├── trends.py            📈 Topic discovery
├── social_poster.py     📤 Publishing
├── requirements.txt     📦 Dependencies
├── .env.example         📝 Config template
├── .env                 🔐 Your secrets (git-ignored)
├── README.md            📖 User docs
├── DEPLOYMENT.md        🚀 Ops guide
└── posts.db             💾 SQLite database
```

---

## 💡 How It Works

1. **Daily (08:00)**: Discovers topics → BMAD picks best → Generates text + image → Schedules posts
2. **Every 2 min**: Checks for due posts → Publishes to Facebook/LinkedIn → Retries failures
3. **Caching**: Identical inputs = $0 cost (cached response)
4. **Retry logic**: 3 attempts with exponential backoff
5. **Logging**: Everything tracked in database

---

## 💰 Cost Breakdown

**Per unique post:**
- Text: $0.001 (gpt-4o-mini)
- Image: $0.040 (DALL-E 3)
- **Total: $0.041**

**Per cached post:** $0.00

**Monthly (30 posts):** ~$0.60-$1.23

---

## 🎯 Customization

### Change posting schedule
Edit `.env`:
```bash
POST_HOUR=14:30  # Post at 2:30 PM
TZ=America/New_York
```

### Change brand voice
Edit `.env`:
```bash
BRAND_NAME=My Company
BRAND_CONTEXT=B2B SaaS, developer tools
BRAND_STYLE=technical + conversational
```

### Add RSS feeds
Edit `.env`:
```bash
TREND_SOURCES=https://news.ycombinator.com/rss,https://example.com/feed.xml
```

---

## 🔗 Getting API Credentials

### OpenAI
1. Go to platform.openai.com
2. Create API key
3. Add to `.env`

### Facebook Page Token
1. Go to developers.facebook.com
2. Create app → Add Facebook Login
3. Graph API Explorer → Get Page Access Token
4. Permissions: `pages_manage_posts`, `pages_read_engagement`
5. Generate long-lived token
6. Add to `.env`

### LinkedIn Access Token
1. Go to linkedin.com/developers
2. Create app
3. Request access to Marketing API
4. OAuth 2.0 flow → Get access token
5. Permissions: `w_member_social` (personal) or `w_organization_social` (company)
6. Add to `.env`

---

## 📞 Support

- **Issues?** Check `PROJECT_SUMMARY.md`
- **Deployment?** See `DEPLOYMENT.md`
- **Documentation?** Read `README.md`

---

## ✅ Quick Checklist

- [ ] Python 3.10+ installed
- [ ] Dependencies installed (`pip install -r requirements.txt`)
- [ ] `.env` file created with all keys
- [ ] Validation passed (`--validate`)
- [ ] Test run successful (`--plan-now`)
- [ ] Scheduler running (`python scheduler.py`)

---

**You're ready to automate your social media!** 🚀
