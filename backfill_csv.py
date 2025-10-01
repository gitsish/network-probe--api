# backfill_csv.py
import os, csv, json, requests
from dotenv import load_dotenv

load_dotenv()   # only for local usage; in CI use env vars

SUPABASE_URL = os.getenv("SUPABASE_URL")
SUPABASE_SERVICE_KEY = os.getenv("SUPABASE_SERVICE_KEY")
TABLE = "probes"
CSV_PATH = "data/metrics.csv"  # adjust path to your file

if not SUPABASE_URL or not SUPABASE_SERVICE_KEY:
    raise SystemExit("Set SUPABASE_URL and SUPABASE_SERVICE_KEY env vars")

def insert_rows(rows):
    url = f"{SUPABASE_URL}/rest/v1/{TABLE}"
    headers = {
        "apikey": SUPABASE_SERVICE_KEY,
        "Authorization": f"Bearer {SUPABASE_SERVICE_KEY}",
        "Content-Type": "application/json",
        "Prefer": "return=minimal"
    }
    # Supabase accepts array inserts
    r = requests.post(url, headers=headers, json=rows, timeout=30)
    r.raise_for_status()
    return r

def read_csv_and_backfill(path):
    rows = []
    with open(path, newline='') as f:
        reader = csv.DictReader(f)
        for r in reader:
            # normalize fields to match your table columns
            # ensure ts is RFC3339 (or let Supabase set now())
            # Example: csv has columns timestamp, host, latency_ms, loss_pct, protocol
            rows.append({
                "ts": r.get("timestamp") or r.get("ts"),
                "host": r.get("host"),
                "latency_ms": float(r["latency_ms"]) if r.get("latency_ms") else None,
                "loss_pct": float(r["loss_pct"]) if r.get("loss_pct") else None,
                "protocol": r.get("protocol") or "icmp"
            })
            # chunk to avoid huge payloads
            if len(rows) >= 100:
                insert_rows(rows)
                rows = []
    if rows:
        insert_rows(rows)

if __name__ == "__main__":
    read_csv_and_backfill(CSV_PATH)
    print("Backfill complete")
