"""
test_db_reliability.py - Test database reliability enhancements
"""
from db import get_db

print("=" * 60)
print("Testing Database Reliability Enhancements")
print("=" * 60)
print()

# Test 1: Basic connection
print("Test 1: Basic Connection")
try:
    with get_db() as db:
        cur = db.execute("SELECT COUNT(*) FROM posts")
        count = cur.fetchone()[0]
        print(f"✅ Database connection successful!")
        print(f"   Found {count} posts in database")
except Exception as e:
    print(f"❌ Connection failed: {e}")

print()

# Test 2: Multiple rapid connections (simulate concurrency)
print("Test 2: Rapid Sequential Connections (Concurrency Simulation)")
try:
    for i in range(5):
        with get_db() as db:
            cur = db.execute("SELECT COUNT(*) FROM logs")
            count = cur.fetchone()[0]
        print(f"   Connection {i+1}/5: ✅ Success ({count} log entries)")
    print("✅ All rapid connections succeeded!")
except Exception as e:
    print(f"❌ Concurrency test failed: {e}")

print()

# Test 3: Write operation
print("Test 3: Write Operation")
try:
    from db import log_event
    log_event("test_reliability", "info", "Database reliability test completed successfully")
    print("✅ Write operation successful!")
except Exception as e:
    print(f"❌ Write failed: {e}")

print()
print("=" * 60)
print("Database Reliability Test Complete!")
print("=" * 60)


