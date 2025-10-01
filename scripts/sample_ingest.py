# scripts/sample_ingest.py
import os, requests
from dotenv import load_dotenv

load_dotenv()

API_URL = "https://web-production-d9ba8.up.railway.app/ingest"
RUN_API_KEY = os.getenv("RUN_API_KEY")  # must be set in .env
headers = {
    "X-API-KEY": RUN_API_KEY,
    "Content-Type": "application/json"
}

sample_row = {
    "timestamp": "2025-10-01T12:34:56Z",
    "host": "9.9.9.9",
    "method": "icmp",
    "avg_ms": 15.2,
    "packet_loss_pct": 0
}

try:
    r = requests.post(API_URL, headers=headers, json=sample_row, timeout=10)
    r.raise_for_status()
    print("✅ Sample row ingested:", r.json())
except Exception as e:
    print("❌ Ingest failed:", e)
