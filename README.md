# AI Auto-Poster (Python)

**Production-lean, environment-driven social media automation system** that discovers trending topics, generates engaging content (text + images via OpenAI), schedules posts, and publishes to Facebook Pages and LinkedIn.

## 🎯 Features

- **Automated Content Discovery**: Fetches trending topics from RSS feeds (HN, NYT, Reddit)
- **AI-Powered Generation**: Uses OpenAI GPT-4o-mini for text and DALL-E-3 for images
- **Multi-Platform Publishing**: Facebook Pages and LinkedIn (personal/organization)
- **Smart Caching**: Minimizes duplicate API calls to reduce costs
- **Cost Tracking**: Monitors and enforces daily/monthly budget limits
- **Retry Logic**: Exponential backoff for API failures
- **Guardrails**: Platform-specific content validation and formatting
- **Scheduled Posting**: APScheduler for automated daily content planning
- **SQLite Storage**: Local database for posts, topics, cache, logs, and costs

## 📁 Project Structure

```
ai-auto-poster/
├── app.py              # CLI entry point
├── scheduler.py        # APScheduler orchestration
├── ai_agent.py         # OpenAI integration (BMAD Supervisor)
├── trends.py           # Topic discovery from RSS feeds
├── social_poster.py    # Facebook & LinkedIn publishing
├── db.py               # SQLite database layer
├── cost.py             # Cost calculation and budget enforcement
├── cache.py            # AI response caching
├── guardrails.py       # Content validation and constraints
├── config.py           # Environment configuration
├── requirements.txt    # Python dependencies
├── .env.example        # Environment variables template
├── .gitignore          # Git ignore rules
└── media/              # Generated images storage
```

## 🚀 Quick Start

### 1. Setup Environment

```bash
# Clone the repository
git clone <your-repo-url>
cd ai-auto-poster

# Create virtual environment
python3 -m venv .venv
source .venv/bin/activate  # On Windows: .venv\Scripts\activate

# Install dependencies
pip install -r requirements.txt
```

### 2. Configure Environment Variables

```bash
# Copy example env file
cp .env.example .env

# Edit .env with your API keys
nano .env
```

Required variables:
- `OPENAI_API_KEY`: Your OpenAI API key
- `FB_PAGE_ID`: Facebook Page ID
- `FB_PAGE_ACCESS_TOKEN`: Facebook Page access token
- `LINKEDIN_ACCESS_TOKEN`: LinkedIn OAuth token
- `LINKEDIN_PERSON_URN` or `LINKEDIN_ORG_URN`: LinkedIn entity URN

### 3. Run the System

```bash
# Option 1: Run scheduler (automated daily posting)
python scheduler.py

# Option 2: Use CLI commands
python app.py schedule       # Run scheduler
python app.py plan-now       # Generate content immediately
python app.py post-now       # Publish scheduled posts
python app.py status         # Show system status
python app.py costs          # Show cost breakdown
python app.py logs --limit 50  # Show recent logs
```

## 🏗️ Architecture

### BMAD Supervisor Pattern

The system implements a **BMAD** (Build, Manage, Architect, Debug) supervisor pattern:

1. **Architect**: Validates modules and interfaces, ensures separation of concerns
2. **Strategist**: Defines prompt patterns and platform constraints
3. **Developer**: Implements Python modules with clean, typed code
4. **Debugger**: Adds input validation, retries, and error logging
5. **Manager**: Enforces delivery in small increments

### Content Generation Flow

```
┌─────────────────┐
│ Discover Topics │ (trends.py)
└────────┬────────┘
         │
         ▼
┌─────────────────┐
│ BMAD Supervisor │ (ai_agent.py)
│ Selects Best    │
└────────┬────────┘
         │
         ▼
┌─────────────────┐
│ Generate Text   │ (ai_agent.py)
│ 3 Variants      │
└────────┬────────┘
         │
         ▼
┌─────────────────┐
│ Generate Image  │ (ai_agent.py)
└────────┬────────┘
         │
         ▼
┌─────────────────┐
│ Apply Guards    │ (guardrails.py)
└────────┬────────┘
         │
         ▼
┌─────────────────┐
│ Schedule Posts  │ (scheduler.py)
└────────┬────────┘
         │
         ▼
┌─────────────────┐
│ Publish         │ (social_poster.py)
│ FB + LinkedIn   │
└─────────────────┘
```

### Database Schema

- **posts**: Scheduled and published posts
- **topics**: Discovered trending topics
- **ai_cache**: Cached OpenAI responses
- **logs**: Structured event logs
- **costs**: API cost tracking

## 💰 Cost Management

The system implements aggressive cost minimization:

1. **Caching**: All OpenAI responses cached by input hash
2. **Batch Processing**: Generate multiple variants in single API call
3. **Budget Limits**: Configurable daily/monthly spending caps
4. **Short Prompts**: Optimized system prompts to minimize tokens
5. **Model Selection**: Uses gpt-4o-mini (cheaper) for text generation

### Approximate Costs (per post)

- Text generation: ~$0.001 - $0.003
- Image generation: ~$0.040
- **Total per post**: ~$0.04 - $0.05
- **Monthly (30 posts)**: ~$1.20 - $1.50

## 🔒 Security Best Practices

- ✅ Never hardcode secrets (all via `.env`)
- ✅ `.env` excluded from git
- ✅ Input validation on all user data
- ✅ SQL injection protection (parameterized queries)
- ✅ API token rotation recommended every 90 days

## 📊 Monitoring

### View Logs

```bash
# SQLite CLI
sqlite3 posts.db "SELECT * FROM logs ORDER BY id DESC LIMIT 20;"

# Python CLI
python app.py logs --limit 50
```

### Check Costs

```bash
# Daily costs
sqlite3 posts.db "SELECT date, SUM(cost_usd) FROM costs GROUP BY date ORDER BY date DESC LIMIT 7;"

# Python CLI
python app.py costs
```

### View Scheduled Posts

```bash
sqlite3 posts.db "SELECT scheduled_at, platform, title FROM posts WHERE status='scheduled';"
```

## 🔧 Configuration Options

### Environment Variables

| Variable | Required | Default | Description |
|----------|----------|---------|-------------|
| `OPENAI_API_KEY` | Yes | - | OpenAI API key |
| `FB_PAGE_ID` | Yes | - | Facebook Page ID |
| `FB_PAGE_ACCESS_TOKEN` | Yes | - | Facebook Page token |
| `LINKEDIN_ACCESS_TOKEN` | Yes | - | LinkedIn OAuth token |
| `LINKEDIN_PERSON_URN` | No | - | Personal account URN |
| `LINKEDIN_ORG_URN` | No | - | Organization URN |
| `DB_PATH` | No | `posts.db` | SQLite database path |
| `MEDIA_DIR` | No | `media` | Image storage directory |
| `TZ` | No | `Europe/Bucharest` | Timezone for scheduling |
| `DAILY_COST_LIMIT_USD` | No | `5.0` | Daily spending cap |
| `MONTHLY_COST_LIMIT_USD` | No | `100.0` | Monthly spending cap |
| `BRAND_BULLETS` | No | (see .env.example) | Brand voice guidelines |

### Scheduler Configuration

Edit `scheduler.py` to customize:
- **Daily planning time**: Default 08:00 (line 214)
- **Posting tick interval**: Default 2 minutes (line 217)
- **Post scheduling delay**: Default +1 hour buffer (line 119)

## 🔮 Future Enhancements (TODOs)

### High Priority
- [ ] Streamlit dashboard for manual post creation/editing
- [ ] Analytics dashboard (engagement metrics)
- [ ] Topic deduplication (fuzzy matching)
- [ ] A/B testing for post variants

### Medium Priority
- [ ] Twitter/X integration
- [ ] Instagram support
- [ ] Webhook notifications (Discord, Slack)
- [ ] Post preview before publishing

### Low Priority
- [ ] Multi-language support
- [ ] Sentiment analysis for topics
- [ ] Competitor content analysis
- [ ] AI-powered engagement response

## 🐛 Troubleshooting

### "Configuration errors: OPENAI_API_KEY"

Ensure `.env` file exists and contains valid API keys.

### "Rate limit exceeded"

System automatically retries with exponential backoff. If persistent, check your OpenAI rate limits.

### "Budget limit exceeded"

Increase limits in `.env`:
```env
DAILY_COST_LIMIT_USD=10.0
MONTHLY_COST_LIMIT_USD=200.0
```

### Posts stuck in "scheduled" status

Run manual publish:
```bash
python app.py post-now
```

Check logs for errors:
```bash
python app.py logs --limit 50
```

## 📝 Development Guidelines

1. **Small Functions**: Keep functions under 50 lines
2. **Type Hints**: Use type annotations where helpful
3. **Error Handling**: Always log errors with context
4. **Idempotency**: Design jobs to be safely retryable
5. **Documentation**: Add docstrings to all public functions

## 📄 License

MIT License - feel free to use and modify for your projects.

## 🤝 Contributing

Contributions welcome! Please:
1. Fork the repository
2. Create a feature branch
3. Add tests if applicable
4. Submit a pull request

## 📧 Support

For issues or questions, please open a GitHub issue.

---

**Built with ❤️ using Python, OpenAI, APScheduler, and SQLite**
