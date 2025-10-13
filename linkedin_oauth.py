"""
linkedin_oauth.py - LinkedIn OAuth 2.0 helper for getting access tokens.
Opens browser for authentication, handles callback, displays tokens.
Run once to get initial access and refresh tokens.
"""
from flask import Flask, request, redirect
import requests
import webbrowser
import os
import sys

app = Flask(__name__)

# Configuration - Update these with your app credentials
CLIENT_ID = os.getenv("LINKEDIN_CLIENT_ID", "")
CLIENT_SECRET = os.getenv("LINKEDIN_CLIENT_SECRET", "")
REDIRECT_URI = "http://localhost:8000/callback"

# Required scopes for Community Management API
SCOPES = [
    "r_organization_social",     # Read organization posts
    "w_organization_social",     # Write organization posts  
    "rw_organization_admin"      # Manage organization
]

@app.route('/')
def index():
    """Redirect to LinkedIn authorization page."""
    if not CLIENT_ID or not CLIENT_SECRET:
        return """
        <h1>❌ Error: Missing Credentials</h1>
        <p>Please set these environment variables:</p>
        <pre>
LINKEDIN_CLIENT_ID=your_client_id
LINKEDIN_CLIENT_SECRET=your_secret
        </pre>
        <p>Or update them directly in linkedin_oauth.py</p>
        """
    
    auth_url = (
        f"https://www.linkedin.com/oauth/v2/authorization"
        f"?response_type=code"
        f"&client_id={CLIENT_ID}"
        f"&redirect_uri={REDIRECT_URI}"
        f"&scope={'+'.join(SCOPES)}"
    )
    return redirect(auth_url)

@app.route('/callback')
def callback():
    """Handle OAuth callback and exchange code for tokens."""
    code = request.args.get('code')
    error = request.args.get('error')
    error_description = request.args.get('error_description')
    
    if error:
        return f"""
        <h1>❌ OAuth Error</h1>
        <p><strong>Error:</strong> {error}</p>
        <p><strong>Description:</strong> {error_description}</p>
        <p>Please try again or check your app configuration.</p>
        """
    
    if not code:
        return """
        <h1>❌ No Authorization Code</h1>
        <p>No authorization code received from LinkedIn.</p>
        <p>Please try again.</p>
        """
    
    # Exchange authorization code for access token
    try:
        token_response = requests.post(
            'https://www.linkedin.com/oauth/v2/accessToken',
            data={
                'grant_type': 'authorization_code',
                'code': code,
                'client_id': CLIENT_ID,
                'client_secret': CLIENT_SECRET,
                'redirect_uri': REDIRECT_URI
            },
            timeout=30
        )
        
        token_response.raise_for_status()
        tokens = token_response.json()
        
        access_token = tokens.get('access_token', 'ERROR')
        refresh_token = tokens.get('refresh_token', 'N/A')
        expires_in = tokens.get('expires_in', 0)
        
        # Calculate expiry
        days = expires_in / 86400
        
        html = f"""
        <!DOCTYPE html>
        <html>
        <head>
            <title>LinkedIn OAuth Success</title>
            <style>
                body {{
                    font-family: Arial, sans-serif;
                    max-width: 800px;
                    margin: 50px auto;
                    padding: 20px;
                    background: #f5f5f5;
                }}
                .container {{
                    background: white;
                    padding: 30px;
                    border-radius: 10px;
                    box-shadow: 0 2px 10px rgba(0,0,0,0.1);
                }}
                h1 {{
                    color: #0073b1;
                }}
                pre {{
                    background: #f0f0f0;
                    padding: 15px;
                    border-radius: 5px;
                    overflow-x: auto;
                    font-size: 12px;
                }}
                .success {{
                    color: #00a000;
                }}
                .info {{
                    background: #e7f3ff;
                    padding: 15px;
                    border-left: 4px solid #0073b1;
                    margin: 20px 0;
                }}
                .warning {{
                    background: #fff3cd;
                    padding: 15px;
                    border-left: 4px solid #ffc107;
                    margin: 20px 0;
                }}
            </style>
        </head>
        <body>
            <div class="container">
                <h1 class="success">✅ LinkedIn OAuth Success!</h1>
                
                <div class="info">
                    <strong>📝 STEP 1:</strong> Copy the tokens below to your <code>.env</code> file
                </div>
                
                <h3>Tokens for .env:</h3>
                <pre>LINKEDIN_ACCESS_TOKEN={access_token}
LINKEDIN_REFRESH_TOKEN={refresh_token}</pre>
                
                <div class="warning">
                    <strong>⏰ Token Expiry:</strong> Access token expires in <strong>{expires_in}</strong> seconds 
                    (<strong>{days:.1f}</strong> days)<br>
                    The system will automatically refresh it using the refresh token.
                </div>
                
                <div class="info">
                    <strong>📝 STEP 2:</strong> Also add your Organization URN to <code>.env</code>:<br>
                    <pre>LINKEDIN_ORG_URN=urn:li:organization:YOUR_ORG_ID</pre>
                    Find your ORG_ID from your LinkedIn company page URL.
                </div>
                
                <div class="info">
                    <strong>🧪 STEP 3:</strong> Test the connection:<br>
                    <code>python linkedin_api_client.py</code>
                </div>
                
                <p><strong>✅ You can close this window and stop the Flask server (Ctrl+C in terminal).</strong></p>
            </div>
        </body>
        </html>
        """
        
        return html
        
    except requests.exceptions.RequestException as e:
        return f"""
        <h1>❌ Token Exchange Failed</h1>
        <p><strong>Error:</strong> {str(e)}</p>
        <p>Please check your Client ID and Client Secret.</p>
        """
    except Exception as e:
        return f"""
        <h1>❌ Unexpected Error</h1>
        <p><strong>Error:</strong> {str(e)}</p>
        <p>Please try again or check the logs.</p>
        """

def main():
    """Main entry point for OAuth flow."""
    print("\n" + "="*60)
    print("🔐 LinkedIn OAuth 2.0 Helper")
    print("="*60)
    
    # Check if credentials are set
    if not CLIENT_ID or not CLIENT_SECRET:
        print("\n❌ ERROR: LinkedIn credentials not found!")
        print("\nPlease set these environment variables:")
        print("  LINKEDIN_CLIENT_ID=your_client_id")
        print("  LINKEDIN_CLIENT_SECRET=your_secret")
        print("\nOr update them directly in this file (linkedin_oauth.py)")
        print("\n" + "="*60 + "\n")
        sys.exit(1)
    
    print(f"\n✅ Client ID found: {CLIENT_ID[:15]}...")
    print(f"✅ Client Secret found: {'*' * 20}")
    print(f"\n📍 Redirect URI: {REDIRECT_URI}")
    print(f"🔐 Scopes: {', '.join(SCOPES)}")
    
    print("\n" + "="*60)
    print("🌐 INSTRUCTIONS:")
    print("="*60)
    print("1. Browser will open for LinkedIn authentication")
    print("2. Login and authorize the app")
    print("3. You'll be redirected to http://localhost:8000/callback")
    print("4. Copy the displayed tokens to your .env file")
    print("5. Press Ctrl+C here to stop the server")
    print("="*60 + "\n")
    
    input("Press Enter to open browser and start OAuth flow...")
    
    # Open browser
    try:
        webbrowser.open('http://localhost:8000/')
    except Exception as e:
        print(f"⚠️  Could not open browser automatically: {e}")
        print("\nPlease manually visit: http://localhost:8000/")
    
    print("\n🚀 Starting OAuth server on http://localhost:8000/")
    print("⏳ Waiting for authentication...")
    print("\n(Press Ctrl+C to stop when done)\n")
    
    # Start Flask server
    try:
        app.run(port=8000, debug=False)
    except KeyboardInterrupt:
        print("\n\n✅ OAuth helper stopped.")
        print("="*60 + "\n")

if __name__ == '__main__':
    main()

