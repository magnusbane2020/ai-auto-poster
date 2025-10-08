"""
trends.py - Topic discovery from RSS feeds and trending sources.
Fetches tech news, trends, and relevant content themes.
Deduplicates and normalizes topics for AI agent consumption.
"""
import feedparser
import hashlib
import json
from datetime import datetime
from db import get_db, log_event

def normalize_topic(s: str) -> str:
    """Generate deterministic topic key from title."""
    s = s.lower().strip()
    return "t:" + hashlib.sha1(s.encode()).hexdigest()[:10]

def discover_topics(max_topics: int = 10) -> list[str]:
    """
    Discover trending topics from RSS feeds.
    Args:
        max_topics: Maximum number of topics to return
    Returns:
        List of unique topic strings
    """
    # RSS sources (add more as needed)
    # TODO: Add API-based sources (Reddit, Twitter/X, Google Trends)
    urls = [
        "https://news.ycombinator.com/rss",
        "https://rss.nytimes.com/services/xml/rss/nyt/Technology.xml",
        "https://www.reddit.com/r/technology/.rss",
    ]
    
    topics = []
<<<<<<< Current (Your changes)
    for u in urls:
        feed = feedparser.parse(u)
        for e in feed.entries[:5]:
            title = (e.title or "").strip()
            if title:
                topics.append(title)
    # ensure at least some topics
    return list(dict.fromkeys(topics[:10]))  # unique, top 10
=======
    errors = []
    
    for url in urls:
        try:
            feed = feedparser.parse(url)
            for entry in feed.entries[:5]:  # Top 5 from each source
                title = (entry.title or "").strip()
                if title and len(title) > 10:  # Minimum length filter
                    topics.append(title)
        except Exception as e:
            errors.append(f"{url}: {str(e)}")
            log_event("trends", "warning", f"Failed to fetch RSS: {url}", {"error": str(e)})
    
    # Deduplicate while preserving order
    unique_topics = list(dict.fromkeys(topics))[:max_topics]
    
    # Store topics in DB for future reference
    with get_db() as db:
        for topic in unique_topics:
            key = normalize_topic(topic)
            try:
                db.execute(
                    "INSERT OR IGNORE INTO topics(key, source, payload_json) VALUES(?,?,?)",
                    (key, "rss_feeds", json.dumps({"title": topic, "discovered": datetime.utcnow().isoformat()}))
                )
            except Exception:
                pass  # Duplicate key, skip
    
    log_event("trends", "info", f"Discovered {len(unique_topics)} topics", {"errors": len(errors)})
    
    # Fallback topics if discovery fails
    if len(unique_topics) < 3:
        fallback = [
            "AI and Machine Learning trends in 2025",
            "Remote work productivity tips",
            "Cybersecurity best practices for businesses",
            "Sustainable technology innovations",
            "Digital transformation strategies"
        ]
        unique_topics.extend(fallback[:max_topics - len(unique_topics)])
        log_event("trends", "warning", "Using fallback topics", {"count": len(fallback)})
    
    return unique_topics[:max_topics]
>>>>>>> Incoming (Background Agent changes)
