import os
from pathlib import Path

import requests
from dotenv import load_dotenv
from purchase_logic import calculate_purchase_quantity

load_dotenv(Path(__file__).with_name(".env"))

url = os.getenv("LLM_GATEWAY_URL", "").strip()
api_key = os.getenv("LLM_GATEWAY_API_KEY", "").strip()
model = os.getenv("LLM_MODEL", "").strip()

if not all([url, api_key, model]):
    raise SystemExit("Missing configuration. Check your .env file.")

product = "Bottled Coffee"
expected_demand = 350
safety_stock = 20
current_stock = 100
incoming_stock = 50

quantity = calculate_purchase_quantity(
    expected_demand,
    safety_stock,
    current_stock,
    incoming_stock,
)

print(f"Product: {product}")
print(f"Recommended purchase: {quantity} units")
print("Getting AI explanation...")

prompt = f"""
Explain this purchasing calculation to a shop owner in 2–3 short sentences.

Product: {product}
Planning period: next week
Expected demand: {expected_demand} units
Safety stock: {safety_stock} units
Current available stock: {current_stock} units
Confirmed incoming stock arriving before needed: {incoming_stock} units
Purchase quantity calculated by Python: {quantity} units

Explain how existing stock and incoming stock reduce the purchase quantity,
and why safety stock is included.
Use only these facts. Do not invent suppliers, prices or sales trends.
Do not claim an order has been placed.
"""

try:
    response = requests.post(
        f"{url.rstrip('/')}/api/chat",
        headers={
            "Content-Type": "application/json",
            "X-API-Key": api_key,
        },
        json={
            "model": model,
            "messages": [{"role": "user", "content": prompt}],
            "stream": False,
            "options": {"num_predict": 200},
        },
        timeout=60,
    )

    if response.ok:
        reply = response.json().get("message", {}).get("content")
        print("\nAI explanation:")
        print(reply or "No explanation returned.")
    else:
        print(f"AI request failed: HTTP {response.status_code}")
        print("The calculated purchase quantity is still available above.")

except requests.exceptions.RequestException:
    print("Could not retrieve an AI explanation. The calculation still works.")
except ValueError:
    print("The gateway returned an unexpected response format.")    