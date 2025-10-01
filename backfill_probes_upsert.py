# backfill_probes_upsert.py
import os
import csv
import requests
from dotenv import load_dotenv

load_dotenv()  # local .env for dev only

SUPABASE_URL = os.getenv("SUPABASE_URL")
SUPABASE_SERVICE_KEY = os.getenv("SUPABASE_SERVICE_KEY")
CSV_PATH = "data/probes.csv"   # adjust if your CSV path differs
TABLE = "probes"
CHUNK_SIZE = 1

if not SUPABASE_URL or not SUPABASE_SERVICE_KEY:
    raise SystemExit("Set SUPABASE_URL and SUPABASE_SERVICE_KEY in env")

def to_float_or_none(v):
    if v is None or v == "":
        return None
    try:
        return float(v)
    except Exception:
        return None

def normalize_row(r):
    ts = r.get("timestamp") or r.get("ts") or None
    host = r.get("host") or r.get("name") or None
    latency = to_float_or_none(r.get("avg_ms") or r.get("latency_ms") or r.get("avg_latency"))
    loss = to_float_or_none(r.get("packet_loss_pct") or r.get("loss_pct") or r.get("loss"))
    protocol = (r.get("method") or r.get("protocol") or "").lower() or None
    try:
        http_status = int(r.get("http_status")) if r.get("http_status") not in (None, "", "[]") else None
    except:
        http_status = None
    raw_rtts = r.get("rtts") or r.get("rtt") or None

    payload = {
        "ts": ts,
        "host": host,
        "latency_ms": latency,
        "loss_pct": loss,
        "protocol": protocol,
        "http_status": http_status,
        "raw_rtts": raw_rtts
    }
    # remove keys with None to let DB defaults handle them
    return {k: v for k, v in payload.items() if v is not None}

def insert_chunk(rows):
    if not rows:
        return
    url = f"{SUPABASE_URL}/rest/v1/{TABLE}?on_conflict=ts,host,protocol"
    headers = {
        "apikey": SUPABASE_SERVICE_KEY,
        "Authorization": f"Bearer {SUPABASE_SERVICE_KEY}",
        "Content-Type": "application/json",
        "Prefer": "resolution=merge-duplicates"
    }
    try:
        resp = requests.post(url, headers=headers, json=rows, timeout=60)
        if resp.status_code >= 400:
            print("=== Failed chunk payload (first row) ===")
            print(rows[0])
            print("=== Response status ===", resp.status_code)
            print("=== Response body ===")
            print(resp.text)
            resp.raise_for_status()
        return resp
    except requests.RequestException as e:
        print("RequestException while inserting chunk:", str(e))
        raise

def backfill(path):
    rows = []
    total = 0
    with open(path, newline='', encoding='utf-8') as f:
        reader = csv.DictReader(f)
        for raw in reader:
            normalized = normalize_row(raw)
            if normalized:
                rows.append(normalized)
            if len(rows) >= CHUNK_SIZE:
                insert_chunk(rows)
                total += len(rows)
                print(f"Inserted {total} rows...")
                rows = []
        if rows:
            insert_chunk(rows)
            total += len(rows)
            print(f"Inserted {total} rows (final).")
    print("Backfill complete, total inserted/attempted:", total)

if __name__ == "__main__":
    backfill(CSV_PATH)
