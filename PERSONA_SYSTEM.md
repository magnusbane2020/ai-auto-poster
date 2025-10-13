# 🎭 Multi-Persona Content Generation System

**Status:** ✅ Fully Implemented  
**Version:** 1.0  
**Date:** 2025-10-08

---

## 📋 Overview

The AI Auto-Poster now features a **sophisticated multi-persona system** that enables diverse, targeted content creation across different voices and audiences. Each persona has its own:

- **Unique tone and style**
- **Dedicated RSS sources**
- **Custom AI prompts**
- **Weighted probability** (ensures proper content mix)
- **Keywords and targeting** (optional)

The system automatically rotates between personas using weighted random selection to maintain content variety and audience engagement.

---

## 🎯 Implemented Personas

### 1. **Magnusbane AI for Enterprises** (60% weight)
**ID:** `magnusbane_ai_enterprise`

**Purpose:** Primary persona educating businesses on AI transformation

**Characteristics:**
- **Tone:** Professional, visionary, confident
- **Style:** LinkedIn thought leadership
- **Target Audience:** B2B, enterprise decision-makers
- **Content Focus:** Real-world AI implementations, business transformation, automation ROI

**RSS Sources:**
- VentureBeat AI
- TechCrunch AI
- McKinsey AI Insights
- Wired AI
- Hacker News

**AI Prompt:**
```
You are Magnusbane AI — an enterprise-level AI strategist.
Write a professional LinkedIn-style post explaining how a recent AI innovation
could be applied by Magnusbane AI to help companies achieve automation, efficiency,
and transformation. Include one clear business insight, one benefit,
and one call to action that inspires B2B readers.
Use an authoritative and inspiring tone.
```

---

### 2. **AI Fun Facts** (25% weight)
**ID:** `fun_facts_ai`

**Purpose:** Light, engaging content that humanizes AI

**Characteristics:**
- **Tone:** Playful, curious, short-form
- **Style:** Twitter/TikTok style
- **Target Audience:** General public, social media users
- **Content Focus:** Surprising AI trivia, humor, accessibility

**RSS Sources:**
- Science Daily AI
- Reddit r/artificial
- Hacker News

**AI Prompt:**
```
You are a fun, witty AI educator who loves surprising people with interesting facts.
Write a short, engaging post (under 300 characters) about a fun or surprising fact
related to AI, automation, or machine learning. Add 1-2 emojis and keep it light-hearted.
Make it shareable and memorable.
```

---

### 3. **AI Trend Tracker** (15% weight)
**ID:** `ai_trends_keywords`

**Purpose:** Tracks trending topics around Magnusbane keywords

**Characteristics:**
- **Tone:** Analytical, modern, trend-driven
- **Style:** Trend commentary and insight analysis
- **Target Audience:** Tech enthusiasts, creators, early adopters
- **Content Focus:** AI, automation, FameUp, TikTok, Amazon trends

**Keywords:** AI, automation, innovation, FameUp, TikTok, Amazon

**RSS Sources:**
- Reddit r/technology
- Hacker News
- TechCrunch
- VentureBeat

**AI Prompt:**
```
You are a tech trend analyst who studies fast-moving digital trends.
Select one topic involving AI, automation, FameUp, TikTok, or Amazon,
and write a brief insight post explaining the trend's business or creative potential.
Include 3-5 relevant hashtags (lowercase) and keep tone data-savvy and modern.
Focus on actionable insights for creators and businesses.
```

---

## ⚙️ How It Works

### Content Generation Flow

```
1. Weighted Random Selection
   └─> 60% Enterprise, 25% Fun Facts, 15% Trends
   
2. Persona-Specific RSS Discovery
   └─> Each persona has unique sources
   
3. Custom AI Prompting
   └─> Persona prompt shapes content tone
   
4. Image Generation
   └─> Tailored to persona style
   
5. Dual Platform Publishing
   └─> Facebook + LinkedIn with guardrails
```

### Weighted Selection Algorithm

```python
# Probabilities over 100 posts:
# - Magnusbane AI: ~60 posts
# - Fun Facts: ~25 posts
# - Trend Tracker: ~15 posts
```

The system uses Python's `random.choices()` with weights to ensure statistically accurate distribution.

---

## 📁 File Structure

```
ai-auto-poster/
├── config/
│   └── personas.yaml          # Persona definitions (YAML)
├── personas.py                 # Persona loader and selector
├── ai_agent.py                 # Updated with persona prompts
├── scheduler.py                # Integrated persona selection
├── trends.py                   # Updated for persona sources
└── app.py                      # New 'personas' command
```

---

## 🚀 Usage Commands

### View Loaded Personas
```bash
py app.py personas
```

**Output:**
```
=== Persona Configuration ===

Loaded 3 personas:

📌 Magnusbane AI for Enterprises
   ID: magnusbane_ai_enterprise
   Weight: 60%
   Tone: Professional, visionary, confident
   Style: LinkedIn thought leadership style...
   Sources: 5 RSS feeds
   Description: The primary persona that educates businesses on AI transformation...

📌 AI Fun Facts
   ID: fun_facts_ai
   Weight: 25%
   ...
```

### Test Weighted Selection
```bash
py app.py personas --test
```

**Output:**
```
🎲 Testing weighted selection (100 samples):

   Magnusbane AI for Enterprises: 58% (expected 60%)
   AI Fun Facts: 27% (expected 25%)
   AI Trend Tracker: 15% (expected 15%)
```

### Generate Content with Persona System
```bash
# Automatic persona selection
py app.py plan-now

# Check which persona was used
py app.py logs --limit 5
```

---

## 🔧 Configuration

### Editing Personas

Edit `config/personas.yaml` to customize:

```yaml
personas:
  - id: "your_custom_persona"
    name: "Your Persona Name"
    weight: 0.20  # 20% of posts
    description: "Your description"
    tone: "Your tone"
    style: "Your style"
    sources:
      - "https://your-rss-feed.com/rss"
    prompt: |
      Your custom AI prompt here.
      Can be multiple lines.
```

**Important:**
- Weights must sum to ~1.0 (system validates this)
- Each persona needs at least 1 RSS source
- Prompts should request JSON output format

### Adding New Personas

1. Add to `config/personas.yaml`
2. Adjust existing weights to accommodate
3. Run `py app.py personas` to validate
4. Test with `py app.py personas --test`

---

## 📊 Persona Analytics

### Track Persona Usage

Persona ID is stored in `topic_key` field:
```sql
SELECT topic_key, COUNT(*) as count
FROM posts
WHERE status='posted'
GROUP BY topic_key;
```

### View in Logs
```bash
py app.py logs --limit 20
```

Look for entries like:
```
ℹ️ [2025-10-08 21:00:00] personas: Selected persona: Magnusbane AI for Enterprises (weight=0.6)
```

---

## 🎨 Image Generation by Persona

The system automatically tailors image prompts to each persona:

| Persona | Image Style |
|---------|-------------|
| Enterprise | Professional, business-grade visualizations |
| Fun Facts | Playful, colorful illustrations |
| Trend Tracker | Modern, data-driven sleek aesthetics |

---

## 💡 Best Practices

### 1. **Weight Distribution**
- Primary persona (enterprise): 50-70%
- Secondary personas: 20-40%
- Experimental personas: 5-15%

### 2. **RSS Source Selection**
- Choose authoritative sources for professional personas
- Use diverse sources for trend tracking
- Include niche sources for specialized personas

### 3. **Prompt Engineering**
- Be specific about tone and format
- Request JSON output explicitly
- Include length constraints (e.g., "under 300 characters")
- Add CTAs and hashtag instructions

### 4. **Content Variety**
- Don't overlap sources too much between personas
- Ensure distinct tones (avoid "professional" for all)
- Use keywords to filter trending content

---

## 🧪 Testing

### Test Individual Persona
```python
from personas import get_persona_manager

pm = get_persona_manager()
persona = pm.get_persona_by_id("fun_facts_ai")
print(persona.prompt)
```

### Test Topic Discovery
```python
from trends import discover_topics
from personas import select_persona

persona = select_persona()
topics = discover_topics(max_topics=10, sources=persona.sources)
print(f"Found {len(topics)} topics for {persona.name}")
```

### Test Content Generation
```bash
# Generate content immediately
py app.py plan-now

# Check generated content
py app.py status
```

---

## 📈 Expected Content Mix (Monthly)

| Persona | Posts/Month | Percentage |
|---------|-------------|------------|
| Enterprise | ~18 | 60% |
| Fun Facts | ~8 | 25% |
| Trend Tracker | ~4 | 15% |
| **Total** | **30** | **100%** |

---

## 🔄 Upgrade Path

### Phase 1: Current (Implemented)
✅ 3 personas with weighted selection  
✅ Unique RSS sources per persona  
✅ Custom AI prompts  
✅ Persona-aware image generation

### Phase 2: Future Enhancements
- [ ] Time-based persona scheduling (e.g., Fun Facts on weekends)
- [ ] Performance tracking by persona (engagement metrics)
- [ ] A/B testing between persona variants
- [ ] Dynamic weight adjustment based on engagement
- [ ] User-defined personas via web UI

---

## 🎯 Success Metrics

Track these to measure persona effectiveness:

1. **Engagement by Persona**
   - Likes/shares per persona type
   - Comment quality and quantity
   - Click-through rates

2. **Audience Growth**
   - Follower increase correlation
   - Demographic shifts

3. **Content Variety Score**
   - Topic diversity index
   - Tone distribution analysis

---

## 🆘 Troubleshooting

### Persona Not Loading
```bash
# Check YAML syntax
py -c "import yaml; yaml.safe_load(open('config/personas.yaml'))"

# Validate personas
py app.py personas
```

### Weights Not Adding to 1.0
System will log warning but continue. Update `config/personas.yaml`:
```yaml
# Ensure weights sum to ~1.0
weight: 0.60  # 60%
weight: 0.25  # 25%
weight: 0.15  # 15%
# Total: 1.00 ✅
```

### RSS Feed Not Working
Check logs:
```bash
py app.py logs --limit 50 | grep "trends"
```

---

## 📚 Related Documentation

- **ARCHITECTURE_STATUS.md** - Full system architecture
- **QUICK_START.md** - Getting started guide
- **README.md** - Project overview

---

**🎭 Persona System v1.0 - Multi-Voice Content Generation**  
*Delivered 2025-10-08*

