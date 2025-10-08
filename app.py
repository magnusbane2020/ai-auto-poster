"""
app.py - Simple CLI interface for testing and manual operations
Provides quick commands for testing individual components.
"""
import sys
from config import CFG, validate_config
from db import get_db, log_event
from trends import discover_topics, get_recent_topics
from ai_agent import generate_text, generate_image, bmad_supervisor
from social_poster import validate_credentials, post_facebook, post_linkedin
from guardrails import enforce_platform_rules


def test_config():
    """Test configuration and credentials."""
    print("🔧 Configuration Test")
    print("=" * 50)
    
    errors = validate_config()
    if errors:
        print("❌ Configuration errors:")
        for err in errors:
            print(f"  - {err}")
        return False
    
    print("✅ Configuration valid\n")
    
    creds = validate_credentials()
    print(f"Facebook: {'✅' if creds['facebook'] else '❌'}")
    print(f"LinkedIn: {'✅' if creds['linkedin'] else '❌'}")
    
    return True


def test_trends():
    """Test trend discovery."""
    print("\n📈 Trend Discovery Test")
    print("=" * 50)
    
    topics = discover_topics(max_topics=5)
    print(f"Discovered {len(topics)} topics:")
    for i, topic in enumerate(topics, 1):
        print(f"{i}. {topic}")
    
    return topics


def test_ai(topics=None):
    """Test AI content generation."""
    print("\n🤖 AI Generation Test")
    print("=" * 50)
    
    if not topics:
        topics = ["The Future of AI in Business", "Cloud Computing Trends 2025"]
    
    brand = ["Tech-focused", "Educational + engaging", "Clear CTA"]
    
    # Test BMAD Supervisor
    print("Testing BMAD Supervisor...")
    plan = bmad_supervisor(topics, brand)
    print(f"Selected: {plan.get('selected_topic', 'N/A')[:50]}...")
    print(f"Style: {plan.get('body_style', 'N/A')}")
    
    # Test text generation
    print("\nGenerating text variants...")
    variants = generate_text(
        topic=plan.get("selected_topic", topics[0]),
        brand_bullets=brand,
        style=plan.get("body_style", "educational"),
        variants=2
    )
    
    for i, var in enumerate(variants.get("variants", []), 1):
        print(f"\nVariant {i}:")
        print(f"Title: {var.get('title', 'N/A')}")
        print(f"Body: {var.get('body', 'N/A')[:100]}...")
    
    return plan, variants


def test_db():
    """Test database operations."""
    print("\n💾 Database Test")
    print("=" * 50)
    
    with get_db() as db:
        # Count records
        posts = db.execute("SELECT COUNT(*) as count FROM posts").fetchone()
        topics = db.execute("SELECT COUNT(*) as count FROM topics").fetchone()
        cache = db.execute("SELECT COUNT(*) as count FROM ai_cache").fetchone()
        logs = db.execute("SELECT COUNT(*) as count FROM logs").fetchone()
        
        print(f"Posts: {posts['count']}")
        print(f"Topics: {topics['count']}")
        print(f"Cache entries: {cache['count']}")
        print(f"Logs: {logs['count']}")
    
    print("\n✅ Database operational")


def show_stats():
    """Show system statistics."""
    print("\n📊 System Statistics")
    print("=" * 50)
    
    with get_db() as db:
        # Post status breakdown
        print("\nPost Status:")
        cur = db.execute("""
            SELECT status, COUNT(*) as count 
            FROM posts 
            GROUP BY status
        """)
        for row in cur:
            print(f"  {row['status']}: {row['count']}")
        
        # Total cost
        cur = db.execute("SELECT SUM(cost_usd) as total FROM posts")
        row = cur.fetchone()
        total_cost = row['total'] if row['total'] else 0
        print(f"\nTotal OpenAI cost: ${total_cost:.4f}")
        
        # Cache hit rate
        cache_count = db.execute("SELECT COUNT(*) as count FROM ai_cache").fetchone()['count']
        print(f"Cache entries: {cache_count}")
        
        # Recent topics
        print("\nRecent Topics:")
        recent = get_recent_topics(limit=5)
        for topic in recent:
            print(f"  - {topic['title'][:60]}...")


def show_recent_posts():
    """Show recent posts."""
    print("\n📝 Recent Posts")
    print("=" * 50)
    
    with get_db() as db:
        cur = db.execute("""
            SELECT platform, title, status, scheduled_at, posted_at, permalink
            FROM posts
            ORDER BY created_at DESC
            LIMIT 10
        """)
        
        for row in cur:
            print(f"\n[{row['platform'].upper()}] {row['title'] or 'Untitled'}")
            print(f"  Status: {row['status']}")
            print(f"  Scheduled: {row['scheduled_at']}")
            if row['posted_at']:
                print(f"  Posted: {row['posted_at']}")
            if row['permalink']:
                print(f"  Link: {row['permalink']}")


def main():
    """Main CLI entry point."""
    if len(sys.argv) < 2:
        print("AI Auto-Poster CLI")
        print("=" * 50)
        print("\nAvailable commands:")
        print("  test-config    - Test configuration and credentials")
        print("  test-trends    - Test trend discovery")
        print("  test-ai        - Test AI content generation")
        print("  test-db        - Test database operations")
        print("  test-all       - Run all tests")
        print("  stats          - Show system statistics")
        print("  posts          - Show recent posts")
        print("\nExample: python app.py test-all")
        return
    
    command = sys.argv[1]
    
    try:
        if command == "test-config":
            test_config()
        
        elif command == "test-trends":
            test_trends()
        
        elif command == "test-ai":
            topics = test_trends()
            test_ai(topics)
        
        elif command == "test-db":
            test_db()
        
        elif command == "test-all":
            test_config()
            topics = test_trends()
            test_ai(topics)
            test_db()
            print("\n✅ All tests completed")
        
        elif command == "stats":
            show_stats()
        
        elif command == "posts":
            show_recent_posts()
        
        else:
            print(f"Unknown command: {command}")
            print("Run 'python app.py' for help")
    
    except Exception as e:
        print(f"\n❌ Error: {e}")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    main()
