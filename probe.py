import os
import json
from datetime import datetime
import requests
from ping3 import ping

# Environment vars (set these in Railway)
SUPABASE_URL = os.getenv("https://ppfpmnvqxqaowmvrjzlk.supabase.co")            # e.g. https://xxxx.supabase.co
SUPABASE_SERVICE_KEY = os.getenv("eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6InBwZnBtbnZxeHFhb3dtdnJqemxrIiwicm9sZSI6InNlcnZpY2Vfcm9sZSIsImlhdCI6MTc1OTMxNjIzOCwiZXhwIjoyMDc0ODkyMjM4fQ.9-l7xVBnU_4cb-or4498FdIRbXdiZ4pb3fcvkM6NAT0")  # service_role key (server-only)
# Table name
TABLE = "probes"

if not SUPABASE_URL or not SUPABASE_SERVICE_KEY:
    raise SystemExit("Missing SUPABASE_URL or SUPABASE_SERVICE_KEY environment variable")

def measure_latency(host: str, timeout=3.0):
    """Return latency in ms or None if no response."""
    try:
        res = ping(host, timeout=timeout, unit="ms")
        if res is None:
            return None
        return float(res)
    except Exception:
        return None

def insert_row_to_supabase(payload: dict):
    url = f"{SUPABASE_URL}/rest/v1/{TABLE}"
    headers = {
        "apikey": SUPABASE_SERVICE_KEY,
        "Authorization": f"Bearer {SUPABASE_SERVICE_KEY}",
        "Content-Type": "application/json",
        "Prefer": "return=representation"
    }
    r = requests.post(url, headers=headers, json=payload, timeout=10)
    r.raise_for_status()
    return r.json()

def run_probe_once(host: str = "1.1.1.1"):
    ts = datetime.utcnow().isoformat()
    latency = measure_latency(host)
    loss_pct = 100.0 if latency is None else 0.0
    latency_val = None if latency is None else round(latency, 2)

    row = {
        "ts": ts,
        "host": host,
        "latency_ms": latency_val,
        "loss_pct": loss_pct,
        "protocol": "icmp"
    }
    inserted = insert_row_to_supabase(row)
    # inserted is list of returned rows (because of Prefer: return=representation)
    return inserted

if __name__ == "__main__":
    print("Running single probe...")
    try:
        res = run_probe_once()
        print("Inserted:", res)
    except Exception as e:
        print("Error running probe:", e)
        raise
