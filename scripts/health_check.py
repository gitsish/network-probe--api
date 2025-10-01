# scripts/health_check.py
import requests

API_URL = "https://web-production-d9ba8.up.railway.app/data?limit=1"

try:
    r = requests.get(API_URL, timeout=10)
    r.raise_for_status()
    json_data = r.json()
    print("✅ API health check passed")
    print("Latest row:", json_data["data"][0] if json_data.get("data") else "no data")
except Exception as e:
    print("❌ API health check failed:", e)
