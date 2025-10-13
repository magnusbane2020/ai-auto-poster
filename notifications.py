"""
notifications.py - Discord and Telegram notification system for post publishing events.
Sends real-time alerts when posts are published to social platforms.
"""
import os
import time
from typing import Optional, Dict
from datetime import datetime
import httpx
from config import CFG
from db import log_event

class NotificationSystem:
    """
    Unified notification system for Discord and Telegram.
    """
    
    def __init__(self):
        self.discord_webhook = os.getenv("DISCORD_WEBHOOK_URL", "")
        self.telegram_bot_token = os.getenv("TELEGRAM_BOT_TOKEN", "")
        self.telegram_chat_id = os.getenv("TELEGRAM_CHAT_ID", "")
        
        self.discord_enabled = bool(self.discord_webhook)
        self.telegram_enabled = bool(self.telegram_bot_token and self.telegram_chat_id)
        
        if not (self.discord_enabled or self.telegram_enabled):
            log_event("notifications", "info", "No notification services configured")
    
    def send_post_notification(self, platform: str, title: str, body: str, 
                              image_path: Optional[str] = None, permalink: Optional[str] = None):
        """
        Send notification when a post is published.
        
        Args:
            platform: Social platform (Facebook, LinkedIn, etc.)
            title: Post title
            body: Post content (truncated)
            image_path: Optional image path
            permalink: Optional post URL
        """
        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        
        # Truncate body for preview
        body_preview = (body[:150] + "...") if len(body) > 150 else body
        
        # Send to Discord
        if self.discord_enabled:
            self._send_discord(platform, title, body_preview, image_path, permalink, timestamp)
        
        # Send to Telegram
        if self.telegram_enabled:
            self._send_telegram(platform, title, body_preview, image_path, permalink, timestamp)
    
    def _send_discord(self, platform: str, title: str, body: str, 
                     image_path: Optional[str], permalink: Optional[str], timestamp: str):
        """
        Send notification to Discord via webhook.
        """
        try:
            # Build embed
            embed = {
                "title": f"✅ {platform} Post Published!",
                "description": f"**{title}**\n\n{body}",
                "color": 5814783,  # Green color
                "fields": [
                    {"name": "Platform", "value": platform, "inline": True},
                    {"name": "Time", "value": timestamp, "inline": True},
                ],
                "footer": {"text": "AI Auto-Poster v3.0"}
            }
            
            # Add permalink if available
            if permalink:
                embed["url"] = permalink
                embed["fields"].append({"name": "Link", "value": f"[View Post]({permalink})", "inline": False})
            
            # Add image if available
            if image_path and os.path.exists(image_path):
                # Discord embeds support image URLs, not local files
                # For now, just indicate image was included
                embed["fields"].append({"name": "Media", "value": "📸 Image included", "inline": True})
            
            payload = {"embeds": [embed]}
            
            with httpx.Client(timeout=10) as client:
                response = client.post(self.discord_webhook, json=payload)
                response.raise_for_status()
                
                log_event("notifications", "info", "Discord notification sent", 
                         {"platform": platform, "title": title[:50]})
                
        except Exception as e:
            log_event("notifications", "error", f"Discord notification failed: {str(e)}")
    
    def _send_telegram(self, platform: str, title: str, body: str,
                      image_path: Optional[str], permalink: Optional[str], timestamp: str):
        """
        Send notification to Telegram via Bot API.
        """
        try:
            # Build message
            message = f"✅ *{platform} Post Published!*\n\n"
            message += f"*{title}*\n\n"
            message += f"{body}\n\n"
            message += f"📅 Time: `{timestamp}`\n"
            
            if permalink:
                message += f"🔗 [View Post]({permalink})\n"
            
            if image_path and os.path.exists(image_path):
                message += f"📸 Image included\n"
            
            message += f"\n_AI Auto-Poster v3.0_"
            
            # Send message
            url = f"https://api.telegram.org/bot{self.telegram_bot_token}/sendMessage"
            payload = {
                "chat_id": self.telegram_chat_id,
                "text": message,
                "parse_mode": "Markdown"
            }
            
            with httpx.Client(timeout=10) as client:
                response = client.post(url, json=payload)
                response.raise_for_status()
                
                log_event("notifications", "info", "Telegram notification sent",
                         {"platform": platform, "title": title[:50]})
                
        except Exception as e:
            log_event("notifications", "error", f"Telegram notification failed: {str(e)}")
    
    def send_error_notification(self, error_type: str, error_message: str, context: Dict = None):
        """
        Send notification when an error occurs.
        
        Args:
            error_type: Type of error (database, posting, generation, etc.)
            error_message: Error description
            context: Additional context information
        """
        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        
        if self.discord_enabled:
            self._send_discord_error(error_type, error_message, context, timestamp)
        
        if self.telegram_enabled:
            self._send_telegram_error(error_type, error_message, context, timestamp)
    
    def _send_discord_error(self, error_type: str, error_message: str, 
                           context: Dict, timestamp: str):
        """Send error notification to Discord."""
        try:
            embed = {
                "title": f"❌ Error: {error_type}",
                "description": error_message,
                "color": 15158332,  # Red color
                "fields": [
                    {"name": "Time", "value": timestamp, "inline": True},
                    {"name": "Type", "value": error_type, "inline": True},
                ],
                "footer": {"text": "AI Auto-Poster v3.0"}
            }
            
            if context:
                for key, value in list(context.items())[:5]:  # Limit to 5 context items
                    embed["fields"].append({"name": str(key), "value": str(value)[:100], "inline": False})
            
            payload = {"embeds": [embed]}
            
            with httpx.Client(timeout=10) as client:
                response = client.post(self.discord_webhook, json=payload)
                response.raise_for_status()
                
        except Exception as e:
            log_event("notifications", "error", f"Discord error notification failed: {str(e)}")
    
    def _send_telegram_error(self, error_type: str, error_message: str,
                            context: Dict, timestamp: str):
        """Send error notification to Telegram."""
        try:
            message = f"❌ *Error: {error_type}*\n\n"
            message += f"{error_message}\n\n"
            message += f"📅 Time: `{timestamp}`\n"
            
            if context:
                message += "\n*Context:*\n"
                for key, value in list(context.items())[:5]:
                    message += f"- {key}: `{str(value)[:50]}`\n"
            
            message += "\n_AI Auto-Poster v3.0_"
            
            url = f"https://api.telegram.org/bot{self.telegram_bot_token}/sendMessage"
            payload = {
                "chat_id": self.telegram_chat_id,
                "text": message,
                "parse_mode": "Markdown"
            }
            
            with httpx.Client(timeout=10) as client:
                response = client.post(url, json=payload)
                response.raise_for_status()
                
        except Exception as e:
            log_event("notifications", "error", f"Telegram error notification failed: {str(e)}")
    
    def send_daily_summary(self, posts_count: int, platforms: list, errors_count: int = 0):
        """
        Send daily summary notification.
        
        Args:
            posts_count: Number of posts published today
            platforms: List of platforms posted to
            errors_count: Number of errors encountered
        """
        timestamp = datetime.now().strftime("%Y-%m-%d")
        
        if self.discord_enabled:
            self._send_discord_summary(posts_count, platforms, errors_count, timestamp)
        
        if self.telegram_enabled:
            self._send_telegram_summary(posts_count, platforms, errors_count, timestamp)
    
    def _send_discord_summary(self, posts_count: int, platforms: list, 
                             errors_count: int, timestamp: str):
        """Send daily summary to Discord."""
        try:
            status_emoji = "✅" if errors_count == 0 else "⚠️"
            
            embed = {
                "title": f"{status_emoji} Daily Summary - {timestamp}",
                "description": f"Automation report for today",
                "color": 3447003 if errors_count == 0 else 16776960,  # Blue or Yellow
                "fields": [
                    {"name": "Posts Published", "value": str(posts_count), "inline": True},
                    {"name": "Errors", "value": str(errors_count), "inline": True},
                    {"name": "Platforms", "value": ", ".join(platforms) if platforms else "None", "inline": False},
                ],
                "footer": {"text": "AI Auto-Poster v3.0"}
            }
            
            payload = {"embeds": [embed]}
            
            with httpx.Client(timeout=10) as client:
                response = client.post(self.discord_webhook, json=payload)
                response.raise_for_status()
                
        except Exception as e:
            log_event("notifications", "error", f"Discord summary notification failed: {str(e)}")
    
    def _send_telegram_summary(self, posts_count: int, platforms: list,
                              errors_count: int, timestamp: str):
        """Send daily summary to Telegram."""
        try:
            status_emoji = "✅" if errors_count == 0 else "⚠️"
            
            message = f"{status_emoji} *Daily Summary - {timestamp}*\n\n"
            message += f"📊 Posts Published: *{posts_count}*\n"
            message += f"❌ Errors: *{errors_count}*\n"
            message += f"📱 Platforms: {', '.join(platforms) if platforms else 'None'}\n"
            message += "\n_AI Auto-Poster v3.0_"
            
            url = f"https://api.telegram.org/bot{self.telegram_bot_token}/sendMessage"
            payload = {
                "chat_id": self.telegram_chat_id,
                "text": message,
                "parse_mode": "Markdown"
            }
            
            with httpx.Client(timeout=10) as client:
                response = client.post(url, json=payload)
                response.raise_for_status()
                
        except Exception as e:
            log_event("notifications", "error", f"Telegram summary notification failed: {str(e)}")


# Singleton instance
_notification_system = None

def get_notification_system() -> NotificationSystem:
    """Get or create singleton notification system instance."""
    global _notification_system
    if _notification_system is None:
        _notification_system = NotificationSystem()
    return _notification_system


def notify_post_published(platform: str, title: str, body: str,
                          image_path: Optional[str] = None, permalink: Optional[str] = None):
    """
    Convenience function to send post publication notification.
    """
    system = get_notification_system()
    system.send_post_notification(platform, title, body, image_path, permalink)


def notify_error(error_type: str, error_message: str, context: Dict = None):
    """
    Convenience function to send error notification.
    """
    system = get_notification_system()
    system.send_error_notification(error_type, error_message, context or {})


def notify_daily_summary(posts_count: int, platforms: list, errors_count: int = 0):
    """
    Convenience function to send daily summary.
    """
    system = get_notification_system()
    system.send_daily_summary(posts_count, platforms, errors_count)


if __name__ == "__main__":
    """Test notifications when run directly."""
    print("🔔 Testing Notification System\n")
    
    # Test post notification
    print("📤 Sending test post notification...")
    notify_post_published(
        platform="LinkedIn",
        title="Test Post",
        body="This is a test notification from AI Auto-Poster v3.0",
        permalink="https://linkedin.com/feed"
    )
    print("✅ Sent!\n")
    
    time.sleep(2)
    
    # Test error notification
    print("📤 Sending test error notification...")
    notify_error(
        error_type="Test Error",
        error_message="This is a test error notification",
        context={"detail": "Testing notifications system"}
    )
    print("✅ Sent!\n")
    
    time.sleep(2)
    
    # Test daily summary
    print("📤 Sending test daily summary...")
    notify_daily_summary(
        posts_count=5,
        platforms=["Facebook", "LinkedIn"],
        errors_count=0
    )
    print("✅ Sent!\n")
    
    print("🎉 All tests complete! Check your Discord/Telegram for messages.")

