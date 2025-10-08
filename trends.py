"""
trends.py - Topic discovery from RSS feeds and trending sources
Fetches latest topics from configurable sources (HN, tech news, etc.).
Deduplicates and normalizes for consistent topic tracking.
TODO: Add Google Trends API, Twitter trending topics, industry-specific feeds.
"""
import hashlib
from typing import Any
from datetime import datetime
import feedparser
from config import CFG
from db import store_topic, log_event


def normalize_topic(text: str) -> str:
    """
    Generate unique, stable key for a topic.
    
    Args:
        text: Topic title/headline
    
    Returns:
        Normalized topic key (e.g., 't:abc123def4')
    """
    normalized = text.lower().strip()
    hash_val = hashlib.sha1(normalized.encode()).hexdigest()[:10]
    return f"t:{hash_val}"


def discover_topics(max_topics: int = 10) -> list[str]:
    """
    Discover trending topics from configured RSS sources.
    
    Args:
        max_topics: Maximum number of topics to return
    
    Returns:
        List of unique topic titles
    """
    sources = CFG.get("TREND_SOURCES", [])
    if not sources:
        sources = [
            "https://news.ycombinator.com/rss",
            "https://rss.nytimes.com/services/xml/rss/nyt/Technology.xml",
        ]
    
    log_event("trends", "INFO", f"Discovering topics from {len(sources)} sources")
    
    topics = []
    seen_keys = set()
    
    for source_url in sources:
        try:
            log_event("trends", "INFO", f"Fetching: {source_url}")
            feed = feedparser.parse(source_url)
            
            if not feed.entries:
                log_event("trends", "WARNING", f"No entries found: {source_url}")
                continue
            
            for entry in feed.entries[:10]:  # Top 10 from each source
                title = (entry.get("title") or "").strip()
                if not title or len(title) < 10:
                    continue
                
                # Deduplicate
                topic_key = normalize_topic(title)
                if topic_key in seen_keys:
                    continue
                
                seen_keys.add(topic_key)
                topics.append(title)
                
                # Store in database for tracking
                payload = {
                    "url": entry.get("link", ""),
                    "summary": entry.get("summary", "")[:500],
                    "published": entry.get("published", ""),
                }
                store_topic(topic_key, source_url, title, payload)
                
                if len(topics) >= max_topics:
                    break
            
            if len(topics) >= max_topics:
                break
        
        except Exception as e:
            log_event("trends", "ERROR", f"Failed to fetch {source_url}: {e}")
            continue
    
    # Fallback if no topics discovered
    if not topics:
        log_event("trends", "WARNING", "No topics discovered, using fallback")
        topics = [
            "The Future of AI in Business",
            "Productivity Hacks for Remote Teams",
            "Cybersecurity Best Practices 2025",
        ]
    
    log_event("trends", "INFO", f"Discovered {len(topics)} topics", {"count": len(topics)})
    return topics[:max_topics]


def get_recent_topics(limit: int = 20) -> list[dict[str, Any]]:
    """
    Retrieve recently discovered topics from database.
    Useful for avoiding duplicate content.
    
    Returns:
        List of topic records with keys, titles, timestamps
    """
    from db import get_db
    
    with get_db() as db:
        cur = db.execute(
            """SELECT key, source, title, discovered_at 
               FROM topics 
               ORDER BY discovered_at DESC 
               LIMIT ?""",
            (limit,)
        )
        return [dict(row) for row in cur.fetchall()]


def filter_used_topics(topics: list[str], days_back: int = 7) -> list[str]:
    """
    Filter out topics that were recently used for posts.
    Prevents repetitive content.
    
    Args:
        topics: List of topic titles
        days_back: Exclude topics used in last N days
    
    Returns:
        Filtered list of unused topics
    """
    from db import get_db
    
    topic_keys = {normalize_topic(t) for t in topics}
    
    with get_db() as db:
        cur = db.execute(
            """SELECT DISTINCT topic_key 
               FROM posts 
               WHERE created_at > datetime('now', ? || ' days')""",
            (f"-{days_back}",)
        )
        used_keys = {row["topic_key"] for row in cur.fetchall() if row["topic_key"]}
    
    # Filter out used topics
    fresh_topics = [t for t in topics if normalize_topic(t) not in used_keys]
    
    log_event("trends", "INFO", f"Filtered {len(topics) - len(fresh_topics)} used topics")
    
    return fresh_topics if fresh_topics else topics  # Return all if nothing new

