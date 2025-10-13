# linkedin_callback.py
from flask import Flask, request
import requests, os

app = Flask(__name__)

CLIENT_ID = "77o6b9fn9a0wvg"
CLIENT_SECRET = os.getenv("LINKEDIN_CLIENT_SECRET")  # pune-l și în .env
REDIRECT_URI = "http://localhost:8000/callback"

@app.route("/callback")
def callback():
    code = request.args.get("code")
    if not code:
        return "No code provided", 400

    # Schimbăm code -> access_token
    token_url = "https://www.linkedin.com/oauth/v2/accessToken"
    data = {
        "grant_type": "authorization_code",
        "code": code,
        "redirect_uri": REDIRECT_URI,
        "client_id": CLIENT_ID,
        "client_secret": CLIENT_SECRET,
    }

    r = requests.post(token_url, data=data)
    if r.status_code != 200:
        return f"Error fetching access token: {r.text}", 400

    token_info = r.json()
    access_token = token_info.get("access_token")

    return f"<h2>✅ Success!</h2><p>Access Token:</p><code>{access_token}</code>"

if __name__ == "__main__":
    app.run(port=8000)
