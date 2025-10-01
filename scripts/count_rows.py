# scripts/count_rows.py
import os, requests
from dotenv import load_dotenv

load_dotenv()  # so it can use your local .env when run locally

SUPABASE_URL = os.getenv("SUPABASE_URL")
SUPABASE_SERVICE_KEY = os.getenv("SUPABASE_SERVICE_KEY")

if not SUPABASE_URL or not SUPABASE_SERVICE_KEY:
    raise SystemExit("Missing SUPABASE_URL or SUPABASE_SERVICE_KEY")

r = requests.get(
    f"{SUPABASE_URL}/rest/v1/probes?select=id",
    headers={
        "apikey": SUPABASE_SERVICE_KEY,
        "Authorization": f"Bearer {SUPABASE_SERVICE_KEY}"
    },
    timeout=30
)
r.raise_for_status()

print("rows:", len(r.json()))
