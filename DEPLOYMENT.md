# AI Auto-Poster - Deployment Guide

## 🎯 System Overview

This is a production-ready, cost-optimized AI Auto-Poster system that:
- Discovers trending topics from RSS feeds
- Uses OpenAI to generate engaging social media content
- Automatically posts to Facebook Pages and LinkedIn
- Implements aggressive caching to minimize API costs
- Includes retry logic, validation, and detailed logging

## 📦 What's Included

### Core Modules

1. **config.py** - Environment-driven configuration
   - Loads all settings from .env
   - Validates required credentials
   - No hardcoded secrets

2. **db.py** - SQLite database management
   - Posts tracking (scheduled, posted, failed)
   - Topics discovery history
   - AI response caching
   - System event logs
   - Automatic schema migrations

3. **cache.py** - AI response caching
   - Caches OpenAI responses by input hash
   - Reduces duplicate API calls to $0
   - Includes cache clearing utilities

4. **guardrails.py** - Content validation
   - Platform-specific rules (LinkedIn: 1300 chars, Facebook: 2000 chars)
   - Link limiting (max 1-2 per platform)
   - Hashtag cleanup and validation
   - Pre-publish content checks

5. **ai_agent.py** - OpenAI integration
   - Text generation with gpt-4o-mini
   - Image generation with DALL-E 3
   - BMAD Supervisor for strategic planning
   - Retry logic with exponential backoff
   - Cost tracking

6. **trends.py** - Topic discovery
   - RSS feed parsing (HackerNews, tech news)
   - Topic deduplication
   - Recently used topic filtering
   - Database storage for tracking

7. **social_poster.py** - Platform publishing
   - Facebook Page posts (text + image)
   - LinkedIn posts (personal/org, text + image)
   - Credential validation
   - Retry logic with exponential backoff

8. **scheduler.py** - Main orchestrator
   - Daily content planning (configurable time)
   - Automated publishing (checks every 2 minutes)
   - CLI commands for testing
   - Startup validation checks

9. **app.py** - Testing & utilities
   - Component testing commands
   - System statistics
   - Recent posts viewer
   - Credential validator

### Configuration Files

- **requirements.txt** - Python dependencies
- **.env.example** - Environment template
- **README.md** - User documentation
- **DEPLOYMENT.md** - This file

## 🚀 Quick Start

### 1. Install Dependencies

```bash
pip install -r requirements.txt
```

### 2. Configure Environment

```bash
cp .env.example .env
```

Edit `.env` with your credentials:

```bash
# Required
OPENAI_API_KEY=sk-...
FB_PAGE_ID=123456789
FB_PAGE_ACCESS_TOKEN=...
LINKEDIN_ACCESS_TOKEN=...
LINKEDIN_PERSON_URN=urn:li:person:...  # OR LINKEDIN_ORG_URN

# Optional customization
BRAND_NAME=Your Brand
BRAND_CONTEXT=Romania context, tech-focused
BRAND_STYLE=educational + funny, no fluff
TZ=Europe/Bucharest
POST_HOUR=09:00
```

### 3. Validate Setup

```bash
python scheduler.py --validate
```

Expected output:
```
🔍 Running startup checks...
✅ Configuration valid
📘 Facebook: ✅
💼 LinkedIn: ✅
✅ Startup checks passed
```

### 4. Test Components

```bash
# Test everything
python app.py test-all

# Test individual components
python app.py test-trends
python app.py test-ai
python app.py test-config
```

### 5. Run One-Time Content Generation

```bash
python scheduler.py --plan-now
```

This will:
1. Discover trending topics
2. Use BMAD Supervisor to select best topic
3. Generate text variants
4. Generate image
5. Schedule posts for LinkedIn + Facebook

### 6. Start Production Scheduler

```bash
python scheduler.py
```

This runs:
- **Daily at configured time** (default 09:00): Content planning
- **Every 2 minutes**: Publishing check

## 📊 Monitoring

### View System Stats

```bash
python app.py stats
```

Shows:
- Post counts by status
- Total OpenAI costs
- Cache entries
- Recent topics

### View Recent Posts

```bash
python app.py posts
```

### Check Logs in Database

```bash
sqlite3 posts.db "SELECT * FROM logs ORDER BY created_at DESC LIMIT 20;"
```

Or in Python:
```python
from db import get_db
with get_db() as db:
    logs = db.execute("SELECT * FROM logs ORDER BY created_at DESC LIMIT 20").fetchall()
    for log in logs:
        print(f"[{log['level']}] {log['scope']}: {log['message']}")
```

## 💰 Cost Management

### Typical Costs Per Post

- **Text generation**: ~$0.001 (gpt-4o-mini)
- **Image generation**: ~$0.040 (DALL-E 3 standard)
- **Total**: ~$0.041 per unique post

### Cost Optimization Features

1. **Aggressive caching**: Identical inputs return cached results ($0 cost)
2. **Short prompts**: Minimizes token usage
3. **Batch operations**: Multiple variants in one API call
4. **Standard quality images**: Uses "standard" not "hd"

### Monitor Costs

```python
from db import get_db
with get_db() as db:
    total = db.execute("SELECT SUM(cost_usd) FROM posts").fetchone()[0]
    print(f"Total spent: ${total:.2f}")
```

## 🗄️ Database Schema

### posts table
```sql
- id: Primary key
- platform: 'linkedin' | 'facebook'
- status: 'scheduled' | 'posted' | 'error'
- title: Post title
- body: Post content
- image_path: Path to generated image
- scheduled_at: When to publish
- posted_at: When published
- permalink: URL to published post
- topic_key: Normalized topic identifier
- cost_usd: API cost for this post
- retry_count: Number of retry attempts
- error_message: Last error if any
- created_at: Record creation time
```

### topics table
```sql
- id: Primary key
- key: Unique topic hash
- source: RSS feed URL
- title: Topic title
- payload_json: Additional metadata
- discovered_at: When discovered
```

### ai_cache table
```sql
- id: Primary key
- cache_key: Short hash prefix
- role: Cache namespace (e.g., 'text_v1')
- input_hash: Full input hash (unique)
- output_text: Cached response
- metadata_json: Additional data (tokens, cost)
- created_at: Cache time
```

### logs table
```sql
- id: Primary key
- scope: Module/function name
- level: 'INFO' | 'WARNING' | 'ERROR'
- message: Log message
- meta_json: Additional context
- created_at: Log time
```

## 🔧 Production Deployment

### Using systemd (Linux)

Create `/etc/systemd/system/ai-auto-poster.service`:

```ini
[Unit]
Description=AI Auto-Poster Scheduler
After=network.target

[Service]
Type=simple
User=youruser
WorkingDirectory=/path/to/ai-auto-poster
Environment="PATH=/usr/bin:/usr/local/bin"
ExecStart=/usr/bin/python3 scheduler.py
Restart=always
RestartSec=10

[Install]
WantedBy=multi-user.target
```

Enable and start:
```bash
sudo systemctl enable ai-auto-poster
sudo systemctl start ai-auto-poster
sudo systemctl status ai-auto-poster
```

### Using Docker

Create `Dockerfile`:
```dockerfile
FROM python:3.11-slim

WORKDIR /app
COPY requirements.txt .
RUN pip install -r requirements.txt

COPY . .

CMD ["python", "scheduler.py"]
```

Build and run:
```bash
docker build -t ai-auto-poster .
docker run -d --name ai-poster --env-file .env ai-auto-poster
```

### Using PM2 (Node.js process manager)

```bash
pm2 start scheduler.py --name ai-auto-poster --interpreter python3
pm2 save
pm2 startup
```

## 🐛 Troubleshooting

### Issue: "No module named 'dotenv'"
**Solution**: Install dependencies
```bash
pip install -r requirements.txt
```

### Issue: "Configuration errors: Missing OPENAI_API_KEY"
**Solution**: Check .env file exists and has correct values
```bash
cat .env | grep OPENAI_API_KEY
```

### Issue: "Facebook credentials invalid"
**Solution**: Regenerate Facebook Page access token
- Go to Facebook Graph API Explorer
- Get Page Access Token with `pages_read_engagement`, `pages_manage_posts` permissions

### Issue: "LinkedIn posting failed"
**Solution**: Check LinkedIn token hasn't expired
- LinkedIn tokens expire after 60 days
- Regenerate using OAuth 2.0 flow

### Issue: "Database locked"
**Solution**: Close other connections
```bash
pkill -f scheduler.py
rm -f posts.db-journal
python scheduler.py
```

## 🔒 Security Best Practices

1. **Never commit .env file**
   - Already in .gitignore
   - Use .env.example as template

2. **Rotate API keys regularly**
   - OpenAI: Every 3-6 months
   - Facebook: When token expires or leaked
   - LinkedIn: Every 60 days (or use refresh tokens)

3. **Limit token permissions**
   - Facebook: Only `pages_manage_posts`, `pages_read_engagement`
   - LinkedIn: Only `w_member_social` or `w_organization_social`

4. **Database backups**
   ```bash
   sqlite3 posts.db .dump > backup_$(date +%Y%m%d).sql
   ```

## 📈 Scaling Considerations

### For Higher Volume

1. **Switch to PostgreSQL**
   - Replace SQLite with PostgreSQL for concurrent writes
   - Update `db.py` with SQLAlchemy

2. **Add Redis caching**
   - Cache hot paths (recent topics, frequent queries)
   - Reduce database load

3. **Horizontal scaling**
   - Separate planning and publishing workers
   - Use message queue (RabbitMQ, Celery)

4. **Rate limiting**
   - Add platform-specific rate limiters
   - Respect API quotas

### For Multiple Brands

1. **Multi-tenant configuration**
   - Add `brand_id` to all tables
   - Separate .env per brand
   - Run multiple scheduler instances

## 🎯 Next Steps / TODOs

- [ ] Add Streamlit UI for manual post approval
- [ ] Implement A/B testing (publish variants, track engagement)
- [ ] Add analytics integration (Facebook Insights, LinkedIn Analytics)
- [ ] Support additional platforms (Instagram, Twitter/X)
- [ ] Implement webhook notifications (Slack, Discord)
- [ ] Add cost budgeting (daily/monthly limits)
- [ ] Topic deduplication (semantic similarity)
- [ ] Export reports (CSV, PDF)

## 📝 Architecture Notes

### Design Principles

1. **Separation of Concerns**: Each module has single responsibility
2. **Fail-Safe**: Extensive error handling and retries
3. **Cost-Conscious**: Aggressive caching and optimization
4. **Environment-Driven**: No hardcoded configs
5. **Idempotent**: Safe to re-run operations
6. **Observable**: Detailed logging and tracking

### Why SQLite?

- Simple deployment (no separate DB server)
- Sufficient for single-instance workload
- Built-in Python support
- Easy backups (just copy file)

For production scale (>1000 posts/day), consider PostgreSQL.

### Why APScheduler?

- Python-native (no external dependencies)
- Flexible scheduling (cron, interval)
- Job persistence options
- Easy to test

For distributed systems, consider Celery + RabbitMQ.

## 🙏 Credits

Built by BMAD Supervisor team using:
- OpenAI API (GPT-4o-mini, DALL-E 3)
- APScheduler for job scheduling
- httpx for HTTP requests
- feedparser for RSS parsing
- tenacity for retries
- SQLite for storage

## 📄 License

MIT License - See LICENSE file

---

**Questions or issues?** Open a GitHub issue or contact the maintainers.
