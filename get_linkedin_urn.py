import requests
import os

token = os.getenv("LINKEDIN_ACCESS_TOKEN")  # sau pune tokenul direct între ghilimele
headers = {"Authorization": f"Bearer {token}"}

response = requests.get("https://api.linkedin.com/v2/me", headers=headers)
print(response.json())
