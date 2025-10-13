"""
test_facebook.py - Test Facebook Graph API integration
Run this to verify your FB_PAGE_ID and FB_PAGE_ACCESS_TOKEN work correctly.

Usage:
  python test_facebook.py
"""
import sys
from config import CFG, validate_config
from social_poster import post_facebook
from db import log_event

def test_facebook_config():
    """Verify Facebook credentials are configured."""
    print("🔍 Checking Facebook configuration...")
    
    page_id = CFG.get("FB_PAGE_ID")
    token = CFG.get("FB_PAGE_ACCESS_TOKEN")
    
    if not page_id:
        print("❌ FB_PAGE_ID is not set in .env")
        return False
    
    if not token:
        print("❌ FB_PAGE_ACCESS_TOKEN is not set in .env")
        return False
    
    print(f"✅ FB_PAGE_ID: {page_id}")
    print(f"✅ FB_PAGE_ACCESS_TOKEN: {token[:20]}... (truncated)")
    return True

def test_facebook_post():
    """Test posting a simple message to Facebook."""
    print("\n📝 Testing Facebook post...")
    
    test_message = """🧪 Test Post from AI Auto-Poster

This is a test post to verify the Facebook Graph API integration is working correctly.

✅ Page ID configured
✅ Access token valid
✅ Permissions granted

Time: """ + str(datetime.now())
    
    try:
        permalink = post_facebook(test_message)
        
        if permalink:
            print(f"\n✅ SUCCESS! Post published to Facebook")
            print(f"🔗 Permalink: {permalink}")
            return True
        else:
            print("⚠️  Post may have succeeded but no permalink returned")
            return True
    except ValueError as e:
        print(f"❌ Configuration error: {e}")
        return False
    except Exception as e:
        print(f"❌ Error posting to Facebook: {e}")
        if hasattr(e, 'response'):
            print(f"Response status: {e.response.status_code}")
            print(f"Response body: {e.response.text}")
        return False

def main():
    print("=" * 60)
    print("Facebook Graph API Integration Test")
    print("=" * 60)
    
    # Check configuration
    errors = validate_config()
    if "FB_PAGE_ID or FB_PAGE_ACCESS_TOKEN" in errors:
        print("\n❌ Facebook credentials missing!")
        print("Please set FB_PAGE_ID and FB_PAGE_ACCESS_TOKEN in your .env file")
        sys.exit(1)
    
    # Test config
    if not test_facebook_config():
        sys.exit(1)
    
    # Confirm before posting
    print("\n⚠️  This will post a TEST MESSAGE to your Facebook Page: Magnusbane")
    response = input("Continue? (yes/no): ")
    
    if response.lower() not in ['yes', 'y']:
        print("Cancelled.")
        sys.exit(0)
    
    # Test posting
    success = test_facebook_post()
    
    print("\n" + "=" * 60)
    if success:
        print("✅ Facebook integration is working correctly!")
        print("\nYou can now:")
        print("  1. Run 'python app.py plan-now' to generate content")
        print("  2. Run 'python app.py post-now' to publish scheduled posts")
        print("  3. Run 'python app.py schedule' for automated posting")
    else:
        print("❌ Facebook integration test failed")
        print("\nTroubleshooting:")
        print("  1. Verify your Page Access Token hasn't expired")
        print("  2. Check permissions in Graph API Explorer")
        print("  3. Ensure FB_PAGE_ID is correct")
        print("  4. Check app is in Live mode (not Development)")
    print("=" * 60)
    
    sys.exit(0 if success else 1)

if __name__ == "__main__":
    from datetime import datetime
    main()

