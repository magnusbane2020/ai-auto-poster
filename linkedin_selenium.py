"""
linkedin_selenium.py - Headless LinkedIn posting automation via Selenium.
Bypasses need for official LinkedIn API access while maintaining reliability.
Requires one-time manual login, then works fully autonomous.
"""
import os
import time
from typing import Optional
from datetime import datetime
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import TimeoutException, NoSuchElementException
from webdriver_manager.chrome import ChromeDriverManager
from db import log_event

# Profile directory for persistent LinkedIn session
# Use user's temp directory to avoid permission issues
import tempfile
TEMP_DIR = tempfile.gettempdir()
PROFILE_DIR = os.path.join(TEMP_DIR, "linkedin_automation_profile")

def _get_chrome_driver(headless: bool = True):
    """
    Create Chrome WebDriver with optimized options for LinkedIn automation.
    
    Args:
        headless: Run in headless mode (no visible browser window)
    Returns:
        Configured WebDriver instance
    """
    chrome_options = Options()
    
    if headless:
        chrome_options.add_argument("--headless=new")
    
    # Performance and stability options
    chrome_options.add_argument("--window-size=1920,1080")
    chrome_options.add_argument("--disable-gpu")
    chrome_options.add_argument("--no-sandbox")
    chrome_options.add_argument("--disable-dev-shm-usage")
    chrome_options.add_argument("--disable-blink-features=AutomationControlled")
    chrome_options.add_argument(f"--user-data-dir={PROFILE_DIR}")
    chrome_options.add_argument("--profile-directory=Default")  # Use Default profile in automation dir
    chrome_options.add_argument("--no-first-run")  # Skip first run wizard
    chrome_options.add_argument("--no-default-browser-check")  # Skip default browser check
    chrome_options.add_argument("--disable-popup-blocking")  # No popups
    chrome_options.add_argument("--disable-extensions")  # No extensions interference
    
    # Reduce detection as bot
    chrome_options.add_experimental_option("excludeSwitches", ["enable-automation", "enable-logging"])
    chrome_options.add_experimental_option('useAutomationExtension', False)
    chrome_options.add_experimental_option("prefs", {
        "credentials_enable_service": False,
        "profile.password_manager_enabled": False,
        "profile.default_content_setting_values.notifications": 2  # Block notifications
    })
    
    # Create service
    service = Service(ChromeDriverManager().install())
    
    driver = webdriver.Chrome(service=service, options=chrome_options)
    
    # Additional anti-detection
    driver.execute_cdp_cmd('Page.addScriptToEvaluateOnNewDocument', {
        'source': 'Object.defineProperty(navigator, "webdriver", {get: () => undefined})'
    })
    
    return driver

def check_login_required() -> bool:
    """
    Check if LinkedIn session is still valid or login is required.
    
    Returns:
        True if login required, False if already logged in
    """
    driver = None
    try:
        driver = _get_chrome_driver(headless=True)
        driver.get("https://www.linkedin.com/feed/")
        
        # Wait up to 10 seconds
        time.sleep(5)
        
        # Check if we're on login page or feed
        current_url = driver.current_url
        
        if "login" in current_url or "checkpoint" in current_url:
            log_event("linkedin_selenium", "warning", "LinkedIn session expired, login required")
            return True
        
        log_event("linkedin_selenium", "info", "LinkedIn session active")
        return False
        
    except Exception as e:
        log_event("linkedin_selenium", "error", f"Failed to check login status: {str(e)}")
        return True
    finally:
        if driver:
            driver.quit()

def post_to_linkedin(message: str, image_path: Optional[str] = None, headless: bool = True) -> str:
    """
    Post to LinkedIn using headless browser automation.
    
    Args:
        message: Post text content
        image_path: Optional path to image file
        headless: Run in headless mode (set False for debugging)
    Returns:
        Success message or empty string on failure
    """
    driver = None
    
    try:
        log_event("linkedin_selenium", "info", "Starting LinkedIn headless posting",
                 {"message_length": len(message), "has_image": bool(image_path), "headless": headless})
        
        # Create driver
        driver = _get_chrome_driver(headless=headless)
        
        # Navigate to LinkedIn feed
        driver.get("https://www.linkedin.com/feed/")
        
        # Wait for page to load
        wait = WebDriverWait(driver, 15)
        
        # Check if login required
        if "login" in driver.current_url or "checkpoint" in driver.current_url:
            log_event("linkedin_selenium", "error", 
                     "LinkedIn session expired. Run with headless=False to re-login.")
            return ""
        
        log_event("linkedin_selenium", "info", "LinkedIn feed loaded successfully")
        
        # Find and click "Start a post" button
        try:
            start_post_btn = wait.until(
                EC.element_to_be_clickable((By.XPATH, 
                    "//button[contains(@class,'share-box-feed-entry__trigger') or contains(@class,'artdeco-button--tertiary')]"))
            )
            start_post_btn.click()
            log_event("linkedin_selenium", "info", "Clicked 'Start a post' button")
            time.sleep(2)
        except TimeoutException:
            log_event("linkedin_selenium", "error", "Could not find 'Start a post' button")
            return ""
        
        # Wait for post modal and find text editor
        try:
            textbox = wait.until(
                EC.presence_of_element_located((By.XPATH, "//div[contains(@class,'ql-editor') or @role='textbox']"))
            )
            textbox.click()
            time.sleep(1)
            textbox.send_keys(message)
            log_event("linkedin_selenium", "info", f"Entered post text ({len(message)} chars)")
            time.sleep(2)
        except TimeoutException:
            log_event("linkedin_selenium", "error", "Could not find text editor")
            return ""
        
        # Add image if provided
        if image_path and os.path.exists(image_path):
            try:
                # Find hidden file input for image upload
                image_input = driver.find_element(By.XPATH, "//input[@type='file' and contains(@accept,'image')]")
                abs_path = os.path.abspath(image_path)
                image_input.send_keys(abs_path)
                
                log_event("linkedin_selenium", "info", f"Uploading image: {image_path}")
                
                # Wait for image to upload (check for image preview)
                time.sleep(5)
                
                # Verify image uploaded
                try:
                    driver.find_element(By.XPATH, "//img[contains(@class,'share-media-image__image')]")
                    log_event("linkedin_selenium", "info", "Image uploaded successfully")
                except NoSuchElementException:
                    log_event("linkedin_selenium", "warning", "Image may not have uploaded correctly")
                    
            except Exception as e:
                log_event("linkedin_selenium", "warning", f"Failed to upload image: {str(e)}")
                # Continue without image
        
        # Find and click Post button
        try:
            # Wait a bit for any uploads to complete
            time.sleep(2)
            
            post_button = wait.until(
                EC.element_to_be_clickable((By.XPATH, 
                    "//button[contains(@class,'share-actions__primary-action') or (contains(@class,'artdeco-button--primary') and contains(.,'Post'))]"))
            )
            post_button.click()
            
            log_event("linkedin_selenium", "info", "Clicked 'Post' button")
            
            # Wait for post to be published
            time.sleep(4)
            
            timestamp = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
            log_event("linkedin_selenium", "info", 
                     f"Successfully posted to LinkedIn via Selenium",
                     {"timestamp": timestamp, "has_image": bool(image_path)})
            
            return timestamp
            
        except TimeoutException:
            log_event("linkedin_selenium", "error", "Could not find 'Post' button")
            return ""
        
    except Exception as e:
        log_event("linkedin_selenium", "error", f"LinkedIn posting failed: {str(e)}")
        return ""
        
    finally:
        if driver:
            driver.quit()

def setup_linkedin_session():
    """
    Interactive setup for LinkedIn session (first-time only).
    Opens browser for manual login, saves session for future automation.
    """
    print("\n" + "="*60)
    print("🔐 LinkedIn Session Setup (One-Time Only)")
    print("="*60)
    print("\nThis will open a browser window for you to login to LinkedIn.")
    print("After logging in, close the browser window.")
    print("Your session will be saved for future automated posts.\n")
    
    input("Press Enter to open browser and login to LinkedIn...")
    
    driver = None
    try:
        # Open browser with profile persistence (NOT headless)
        driver = _get_chrome_driver(headless=False)
        driver.get("https://www.linkedin.com/login")
        
        print("\n✅ Browser opened!")
        print("📝 Please login to LinkedIn in the browser window.")
        print("⏳ After logging in successfully, close the browser window.")
        print("   (Your session will be automatically saved)\n")
        
        # Wait for user to manually close browser
        while True:
            try:
                _ = driver.current_url
                time.sleep(2)
            except:
                # Browser closed by user
                break
        
        print("\n✅ LinkedIn session saved!")
        print("🚀 You can now use automated LinkedIn posting.\n")
        print("="*60 + "\n")
        
        log_event("linkedin_selenium", "info", "LinkedIn session setup completed")
        
    except Exception as e:
        print(f"\n❌ Setup failed: {e}\n")
        log_event("linkedin_selenium", "error", f"Session setup failed: {str(e)}")
    finally:
        if driver:
            try:
                driver.quit()
            except:
                pass

if __name__ == "__main__":
    """Run setup when executed directly."""
    print("🔧 LinkedIn Selenium Automation Setup")
    
    # Check if session exists
    if os.path.exists(PROFILE_DIR):
        print(f"\n✅ Profile directory exists: {PROFILE_DIR}")
        print("Checking if login required...")
        
        if check_login_required():
            print("⚠️  Session expired or invalid")
            setup_linkedin_session()
        else:
            print("✅ Session valid!")
            print("\nTest posting (or press Ctrl+C to skip):")
            test_post = input("Enter test message (or leave empty to skip): ")
            
            if test_post:
                result = post_to_linkedin(test_post, headless=False)
                if result:
                    print(f"\n✅ Test post successful at {result}")
                else:
                    print("\n❌ Test post failed")
    else:
        print(f"\n⚠️  No profile directory found")
        setup_linkedin_session()
