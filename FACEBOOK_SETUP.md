# Facebook Graph API Integration - Setup Complete ✅

## Current Status
Your Facebook integration for "Magnusbane" page is ready to test!

### ✅ Completed Setup
- [x] Facebook App created in Meta Developer
- [x] All required permissions granted:
  - `pages_show_list`
  - `business_management`
  - `pages_manage_posts`
  - `pages_read_engagement`
  - `pages_manage_metadata`
  - `pages_read_user_content`
- [x] Page Access Token and Page ID configured in `.env`
- [x] Code implementation complete with retry logic
- [x] Duplicate code bug fixed in LinkedIn posting

## Environment Variables (in your .env)
```env
FB_PAGE_ID=your-facebook-page-id
FB_PAGE_ACCESS_TOKEN=your-page-access-token
```

## Testing the Integration

### Step 1: Test Facebook Connection
```bash
# Run the test script
python test_facebook.py
```

This will:
1. ✅ Verify your FB credentials are configured
2. ✅ Post a test message to your Facebook Page
3. ✅ Return the permalink if successful

### Step 2: Generate and Post Content Manually

#### Generate content immediately:
```bash
python app.py plan-now
```

This will:
- Discover trending topics
- Use AI to generate post text + image
- Schedule posts for Facebook & LinkedIn (+1 hour from now)

#### Publish scheduled posts immediately:
```bash
python app.py post-now
```

This publishes any scheduled posts that are due.

### Step 3: Run Automated Scheduler
```bash
python app.py schedule
# or
python scheduler.py
```

This starts the automated system:
- **Daily planning**: 08:00 (discovers topics & generates content)
- **Posting tick**: Every 2 minutes (publishes scheduled posts)

## Monitoring Commands

### Check System Status
```bash
python app.py status
```

Shows:
- Configuration validation
- Posts by status (scheduled/posted/error)
- Next scheduled post
- Daily/monthly costs

### View Logs
```bash
python app.py logs --limit 50
```

### Check Costs
```bash
python app.py costs
```

## Facebook API Implementation

### Location: `social_poster.py` (lines 41-87)

**Features:**
- ✅ Supports text-only posts
- ✅ Supports posts with images
- ✅ Automatic retry with exponential backoff
- ✅ Returns permalink URL
- ✅ Error logging with context

**API Endpoint:**
```
https://graph.facebook.com/v21.0/{page_id}/feed       (text only)
https://graph.facebook.com/v21.0/{page_id}/photos     (with image)
```

### Text-Only Post Example:
```python
from social_poster import post_facebook

permalink = post_facebook("Hello from AI Auto-Poster! 🚀")
print(f"Posted: {permalink}")
```

### Post with Image:
```python
permalink = post_facebook(
    message="Check out this AI-generated image!",
    image_path="media/my_image.png"
)
```

## Troubleshooting

### Issue: "FB_PAGE_ID and FB_PAGE_ACCESS_TOKEN required"
**Solution:** Ensure your `.env` file has both values set:
```bash
cat .env | grep FB_
```

### Issue: HTTP 400 Error
**Possible causes:**
1. Access token expired (tokens last 60 days by default)
2. Missing permissions
3. App in Development mode instead of Live mode

**Solution:**
- Regenerate token in Graph API Explorer
- Verify all permissions are granted
- Check app mode in Meta Developer

### Issue: HTTP 190 Error (Token Expired)
**Solution:**
1. Go to [Graph API Explorer](https://developers.facebook.com/tools/explorer/)
2. Select your app
3. Select your page
4. Grant all permissions
5. Click "Generate Access Token"
6. Update `FB_PAGE_ACCESS_TOKEN` in `.env`

### Issue: Posts not publishing
**Check:**
```bash
# View scheduled posts
sqlite3 posts.db "SELECT * FROM posts WHERE status='scheduled';"

# View error posts
sqlite3 posts.db "SELECT id, platform, error_message FROM posts WHERE status='error';"

# Check logs
python app.py logs --limit 20
```

## Content Flow

```
1. Discover Topics (trends.py)
   └─> RSS feeds: HN, NYT, Reddit
   
2. BMAD Supervisor (ai_agent.py)
   └─> Selects best topic & strategy
   
3. Generate Text (ai_agent.py)
   └─> 3 variants, picks best
   
4. Generate Image (ai_agent.py)
   └─> DALL-E-3 based on topic
   
5. Apply Guardrails (guardrails.py)
   └─> Platform-specific limits
   
6. Schedule Posts (scheduler.py)
   └─> Facebook + LinkedIn
   
7. Publish (social_poster.py)
   └─> Graph API with retry logic
```

## API Costs (Approximate)

Per post:
- Text generation: $0.001 - $0.003
- Image generation: $0.040
- **Total: ~$0.04 per post**

Monthly (30 posts):
- **~$1.20 - $1.50**

## Next Steps

1. ✅ Run `python test_facebook.py` to verify integration
2. ✅ Run `python app.py plan-now` to generate first content
3. ✅ Check the generated post in database
4. ✅ Run `python app.py post-now` to publish
5. ✅ Verify post appears on Facebook Page
6. ✅ Start scheduler for automation: `python app.py schedule`

## Production Checklist

Before going live:
- [ ] Facebook App is in **Live** mode (not Development)
- [ ] Access token is **Page Access Token** (not User Access Token)
- [ ] Token has **60+ days** validity
- [ ] All 6 permissions are granted
- [ ] `DAILY_COST_LIMIT_USD` and `MONTHLY_COST_LIMIT_USD` set appropriately
- [ ] Test posts work correctly
- [ ] Monitoring/logging reviewed

## Support

If issues persist:
1. Check logs: `python app.py logs --limit 50`
2. Verify Graph API Explorer can post to your page
3. Check app permissions in Meta Developer
4. Ensure page is not restricted/banned

---

**Built with ❤️ for automated social media posting**

