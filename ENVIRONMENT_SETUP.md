# 🔐 Environment Setup Guide

## 📝 .env Configuration

Create a `.env` file in the root directory with the following variables:

```bash
# ============================================================
# AI AUTO-POSTER - Environment Configuration
# ============================================================

# ============================================================
# REQUIRED: OpenAI API
# ============================================================
OPENAI_API_KEY=sk-your-openai-api-key-here

# ============================================================
# REQUIRED: Facebook Page
# ============================================================
FB_PAGE_ID=your-facebook-page-id
FB_PAGE_ACCESS_TOKEN=your-facebook-page-access-token

# ============================================================
# REQUIRED: LinkedIn
# ============================================================
LINKEDIN_ACCESS_TOKEN=your-linkedin-access-token
# Set ONE of these (personal account OR organization page):
LINKEDIN_PERSON_URN=urn:li:person:XXXXXXXXXX
# OR
LINKEDIN_ORG_URN=urn:li:organization:XXXXXXXXXX

# ============================================================
# OPTIONAL: Canva API Integration (v2.3+)
# ============================================================
# Enable Canva for professional branded image generation
# If disabled or fails, system automatically falls back to DALL-E
USE_CANVA=false
CANVA_API_KEY=your-canva-api-key
CANVA_TEAM_ID=your-canva-team-id
CANVA_BRAND_TEMPLATE_ID=your-template-id

# ============================================================
# System Configuration
# ============================================================
DB_PATH=posts.db
MEDIA_DIR=media
TZ=Europe/Bucharest
POST_HOUR=09:00

# ============================================================
# Budget Limits
# ============================================================
DAILY_COST_LIMIT_USD=5.0
MONTHLY_COST_LIMIT_USD=100.0

# ============================================================
# Brand Voice
# ============================================================
# Comma-separated list of brand guidelines
BRAND_BULLETS=Romania context,tech + educational,no fluff
```

---

## 🎨 Canva API Setup (Optional)

### Step 1: Get Canva Pro Account
1. Sign up at [canva.com/pro](https://www.canva.com/pro)
2. Ensure you have a Pro or Enterprise account

### Step 2: Access Developer Portal
1. Visit [canva.dev](https://www.canva.dev) (when available)
2. Sign in with your Canva account
3. Note: Canva API is currently in beta - request access if needed

### Step 3: Create API Key
1. Navigate to "Apps & Integrations"
2. Click "Create new app"
3. Copy your API key to `CANVA_API_KEY`

### Step 4: Get Team ID
1. Go to Canva → Settings → Team
2. Copy your Team ID to `CANVA_TEAM_ID`

### Step 5: Create Brand Template
1. Create a new design (Social Media Post, 1080x1080)
2. Design your brand template with your colors, fonts, logo
3. Leave space for dynamic content (the system will add text)
4. Copy the design/template ID to `CANVA_BRAND_TEMPLATE_ID`

### Step 6: Enable in Config
```bash
USE_CANVA=true
```

---

## 🧪 Verify Setup

### Test 1: Basic Configuration
```python
python -c "from config import validate_config; errors = validate_config(); print('✅ Config valid' if not errors else f'❌ Missing: {errors}')"
```

### Test 2: Database Health
```bash
python db_monitor.py
```

### Test 3: Canva Integration (if enabled)
```python
python -c "from canva_client import generate_canva_image; img, src = generate_canva_image('Test', 'media/test.png'); print(f'✅ Canva works: {src}' if src == 'canva' else f'⚠️ Canva: {src}')"
```

### Test 4: Full System
```bash
python app.py
# Visit http://localhost:5000
```

---

## 🔒 Security Notes

1. **Never commit .env** - Already in `.gitignore`
2. **Rotate keys regularly** - Especially access tokens
3. **Use environment-specific configs** - Dev vs Production
4. **Limit token permissions** - Only what's needed

---

## 📊 Cost Estimates

### OpenAI
- **Text (GPT-4o-mini):** ~$0.002 per post
- **Images (DALL-E 3):** ~$0.04-0.08 per image

### Canva (if enabled)
- **API Usage:** ~$0.10 per design creation + export
- **Quality:** ⭐⭐⭐⭐⭐ (better brand consistency)

### Daily Estimate
- 2 posts/day × ($0.002 text + $0.10 image) = **~$0.20/day**
- Monthly: **~$6/month**

---

## 🚨 Troubleshooting

### Missing .env file
```bash
# Check if .env exists
ls -la .env

# If not, create it
touch .env
# Then add your configuration
```

### Invalid credentials
```python
from config import validate_config
print(validate_config())
```

### Canva not available
- Set `USE_CANVA=false` in `.env`
- System will automatically use DALL-E

---

## ✅ Setup Complete Checklist

- [ ] `.env` file created
- [ ] OpenAI API key set
- [ ] Facebook credentials set
- [ ] LinkedIn credentials set
- [ ] (Optional) Canva credentials set
- [ ] Budget limits configured
- [ ] Brand voice defined
- [ ] Config validation passes
- [ ] Database health check passes
- [ ] Test post generated successfully

---

**Next Step:** Run `python app.py` to start the system! 🚀

See `DB_CANVA_INTEGRATION_GUIDE.md` for full documentation.

