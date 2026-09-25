import os
from pathlib import Path

import requests
from dotenv import load_dotenv

load_dotenv(Path(__file__).with_name(".env"))

url = os.getenv("LLM_GATEWAY_URL", "").strip()
api_key = os.getenv("LLM_GATEWAY_API_KEY", "").strip()
model = os.getenv("LLM_MODEL", "").strip()

if not all([url, api_key, model]):
    raise SystemExit("Missing configuration. Check the three values in .env.")

print("Connecting to the AI gateway...")

try:
    response = requests.post(
        f"{url.rstrip('/')}/api/chat",
        headers={
            "Content-Type": "application/json",
            "X-API-Key": api_key,
        },
        json={
            "model": model,
            "messages": [
                {
                    "role": "user",
                    "content": "Say hello in one short sentence.",
                }
            ],
            "stream": False,
            "options": {"num_predict": 100},
        },
        timeout=60,
    )

    print(f"HTTP status: {response.status_code}")

    if response.ok:
        data = response.json()
        reply = data.get("message", {}).get("content")
        if reply:
            print("AI:", reply)
        else:
            print("Received JSON, but no message.content was found.")
    else:
        print("Request failed. Share the HTTP status for troubleshooting.")

except requests.exceptions.Timeout:
    print("Request timed out. No response received within 60 seconds.")
except requests.exceptions.ConnectionError:
    print("Connection failed. Check your internet connection and gateway URL.")
except requests.exceptions.JSONDecodeError:
    print("The gateway returned a response that was not valid JSON.")
except requests.exceptions.RequestException:
    print("The request failed before it could complete.")