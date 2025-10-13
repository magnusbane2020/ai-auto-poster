"""
trends.py - Topic discovery from RSS feeds and trending sources.
Fetches tech news, trends, and relevant content themes.
Deduplicates and normalizes topics for AI agent consumption.
Supports persona-specific source filtering.
"""
import feedparser
import hashlib
import json
from datetime import datetime
from typing import Optional
from db import get_db, log_event

def normalize_topic(s: str) -> str:
    """Generate deterministic topic key from title."""
    s = s.lower().strip()
    return "t:" + hashlib.sha1(s.encode()).hexdigest()[:10]

def discover_topics(max_topics: int = 10, sources: Optional[list[str]] = None) -> list[str]:
    """
    Discover trending topics from RSS feeds.
    Args:
        max_topics: Maximum number of topics to return
        sources: Optional list of RSS feed URLs (uses default if None)
    Returns:
        List of unique topic strings
    """
    # Default RSS sources if none provided
    if sources is None:
        sources = [
            "https://news.ycombinator.com/rss",
            "https://rss.nytimes.com/services/xml/rss/nyt/Technology.xml",
            "https://www.reddit.com/r/technology/.rss",
        ]
    
    topics = []
    for url in sources:
        try:
            feed = feedparser.parse(url)
            for entry in feed.entries[:5]:  # Top 5 from each source
                title = (entry.title or "").strip()
                if title:
                    topics.append(title)
        except Exception as e:
            log_event("trends", "warning", f"Failed to fetch RSS from {url[:50]}", {"error": str(e)})
            continue
    
    # Deduplicate while preserving order
    unique_topics = list(dict.fromkeys(topics))
    
    # Return requested number
    result = unique_topics[:max_topics]
    
    log_event("trends", "info", f"Discovered {len(result)} topics from {len(sources)} sources")
    
    return result
