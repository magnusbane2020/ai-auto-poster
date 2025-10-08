import feedparser, hashlib
from datetime import datetime

def normalize_topic(s: str) -> str:
    s = s.lower().strip()
    return "t:" + hashlib.sha1(s.encode()).hexdigest()[:10]

def discover_topics():
    # Example: read tech RSS + a static fallback
    urls = [
        "https://news.ycombinator.com/rss",
        "https://rss.nytimes.com/services/xml/rss/nyt/Technology.xml",
    ]
    topics = []
    for u in urls:
        feed = feedparser.parse(u)
        for e in feed.entries[:5]:
            title = (e.title or "").strip()
            if title:
                topics.append(title)
    # ensure at least some topics
    return list(dict.fromkeys(topics[:10]))  # unique, top 10
