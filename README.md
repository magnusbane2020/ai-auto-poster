# AI Auto-Poster

Automated social media content generation and scheduling system for Facebook Pages and LinkedIn.

## 🚀 Features

- **Trend Discovery**: Automatically fetches trending topics from RSS feeds (HackerNews, tech news)
- **AI Content Generation**: Uses OpenAI GPT-4o-mini for text and DALL-E 3 for images
- **Smart Caching**: Aggressive caching to minimize API costs
- **Platform Optimization**: Applies platform-specific rules for LinkedIn and Facebook
- **Scheduled Publishing**: Automated daily content planning and posting
- **Retry Logic**: Exponential backoff for failed API calls
- **Cost Tracking**: Monitors OpenAI API usage and costs

## 📋 Prerequisites

- Python 3.10+
- OpenAI API key
- Facebook Page access token
- LinkedIn access token (personal or organization)

## 🛠️ Installation

1. Clone the repository:
```bash
git clone <repo-url>
cd ai-auto-poster
```

2. Install dependencies:
```bash
pip install -r requirements.txt
```

3. Configure environment:
```bash
cp .env.example .env
# Edit .env with your API keys and credentials
```

## ⚙️ Configuration

Edit `.env` file with your credentials:

```bash
# OpenAI
OPENAI_API_KEY=sk-...

# Facebook
FB_PAGE_ID=your_page_id
FB_PAGE_ACCESS_TOKEN=your_token

# LinkedIn
LINKEDIN_ACCESS_TOKEN=your_token
LINKEDIN_PERSON_URN=urn:li:person:XXXXX  # OR
LINKEDIN_ORG_URN=urn:li:organization:XXXXX

# Customize brand voice
BRAND_NAME=Your Brand
BRAND_CONTEXT=Romania context, tech-focused
BRAND_STYLE=educational + funny, no fluff
```

## 🏃 Running the System

### Start the scheduler (production mode):
```bash
python scheduler.py
```

### Run one-time tasks:
```bash
# Generate content immediately
python scheduler.py --plan-now

# Publish scheduled posts now
python scheduler.py --post-now

# Validate API credentials
python scheduler.py --validate
```

### Testing individual components:
```bash
# Test all components
python app.py test-all

# Test specific components
python app.py test-config
python app.py test-trends
python app.py test-ai

# Show statistics
python app.py stats
python app.py posts
```

## 📁 Project Structure

```
ai-auto-poster/
├── scheduler.py        # Main orchestrator (entry point)
├── app.py             # CLI for testing components
├── config.py          # Environment configuration
├── db.py              # SQLite database management
├── cache.py           # AI response caching
├── guardrails.py      # Content validation rules
├── ai_agent.py        # OpenAI integration
├── trends.py          # Topic discovery
├── social_poster.py   # Facebook/LinkedIn publishing
├── requirements.txt   # Python dependencies
├── .env.example       # Environment template
└── media/            # Generated images
```

## 🔄 Workflow

1. **Daily Planning (08:00)**: 
   - Discover trending topics from RSS feeds
   - BMAD Supervisor selects best topic
   - Generate 3 text variants, pick best
   - Generate image via DALL-E
   - Apply platform-specific guardrails
   - Schedule posts for both platforms

2. **Publishing (every 2 minutes)**:
   - Check for due posts
   - Publish to Facebook/LinkedIn
   - Retry failed posts (up to 3 attempts)
   - Store permalinks

## 💰 Cost Optimization

- **Aggressive caching**: Identical prompts return cached results ($0 cost)
- **Short prompts**: Optimized for minimal token usage
- **Batch operations**: Generate multiple variants in one API call
- **Standard quality**: Uses DALL-E "standard" mode (cheaper than "hd")

Typical costs per post:
- Text generation: ~$0.001 (cached: $0)
- Image generation: ~$0.040 (cached: $0)
- **Total: ~$0.041 per unique post**

## 🗄️ Database Schema

### Tables
- `posts`: Generated and published posts
- `topics`: Discovered trending topics
- `ai_cache`: OpenAI response cache
- `logs`: System events and errors

## 🔍 Monitoring

Check logs in database:
```python
from db import get_db
with get_db() as db:
    logs = db.execute("SELECT * FROM logs ORDER BY created_at DESC LIMIT 20").fetchall()
    for log in logs:
        print(f"[{log['level']}] {log['scope']}: {log['message']}")
```

Or use the CLI:
```bash
sqlite3 posts.db "SELECT * FROM logs ORDER BY created_at DESC LIMIT 20;"
```

## 🚧 TODO/Future Enhancements

- [ ] Add Streamlit UI for manual post approval
- [ ] Implement A/B testing across variants
- [ ] Add analytics tracking (engagement, reach)
- [ ] Support Instagram, Twitter/X
- [ ] Deduplicate similar topics across days
- [ ] Add cost budget limits per day/month
- [ ] Webhook notifications for published posts
- [ ] Export analytics to CSV/dashboard

## 🐛 Troubleshooting

### "No valid credentials found"
- Check `.env` file exists and has correct values
- Validate tokens using: `python scheduler.py --validate`

### "Cache import error"
- Ensure all dependencies installed: `pip install -r requirements.txt`
- Check Python version: `python --version` (must be 3.10+)

### "Database locked"
- Close any sqlite3 connections
- Restart the scheduler

## 📝 License

MIT License - see LICENSE file for details

## 🤝 Contributing

Contributions welcome! Please open an issue or PR.

---

Built with ❤️ using OpenAI, APScheduler, and SQLite
