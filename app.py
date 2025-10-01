import os
from fastapi import FastAPI, BackgroundTasks, HTTPException, Body, Request
from fastapi.responses import JSONResponse
from fastapi.middleware.cors import CORSMiddleware
import requests

# Import probe runner
from probe import run_probe_once

# Environment
SUPABASE_URL = os.getenv("SUPABASE_URL")
SUPABASE_SERVICE_KEY = os.getenv("SUPABASE_SERVICE_KEY")
SUPABASE_ANON_KEY = os.getenv("SUPABASE_ANON_KEY")  # optional for public reads
RUN_API_KEY = os.getenv("RUN_API_KEY")  # simple API key to protect /run and /ingest

if not SUPABASE_URL or not SUPABASE_SERVICE_KEY:
    raise SystemExit("SUPABASE_URL and SUPABASE_SERVICE_KEY must be set")

app = FastAPI(title="Probe API")

# For testing you can use "*" then lock down to your Streamlit origin later
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

def check_api_key(req: Request):
    """Raise HTTPException 401 if RUN_API_KEY is set and header doesn't match."""
    if RUN_API_KEY:
        header_key = req.headers.get("x-api-key") or req.headers.get("X-API-KEY")
        if not header_key or header_key != RUN_API_KEY:
            raise HTTPException(status_code=401, detail="Invalid or missing API key")

def fetch_data_from_supabase(limit: int = 50):
    headers = {
        "apikey": SUPABASE_SERVICE_KEY,
        "Authorization": f"Bearer {SUPABASE_SERVICE_KEY}"
    }
    url = f"{SUPABASE_URL}/rest/v1/probes?select=*&order=ts.desc&limit={limit}"
    r = requests.get(url, headers=headers, timeout=10)
    r.raise_for_status()
    return r.json()

def background_probe_task(host: str = "1.1.1.1"):
    try:
        run_probe_once(host=host)
    except Exception as e:
        # log error — in Railway you can read logs
        print("Background probe error:", e)

@app.post("/run")
async def run_probe(request: Request, background_tasks: BackgroundTasks, host: str = "1.1.1.1"):
    """
    Trigger a single probe in the background. Use POST /run?host=example.com
    Protected by RUN_API_KEY if set.
    """
    check_api_key(request)
    background_tasks.add_task(background_probe_task, host)
    return JSONResponse({"status": "started", "host": host})
@app.get("/ping")
async def ping():
    return {"status": "ok"}

@app.get("/data")
async def get_data(limit: int = 50):
    try:
        data = fetch_data_from_supabase(limit)
        return {"count": len(data), "data": data}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/ingest")
async def ingest_rows(request: Request, payload: dict = Body(...)):
    """
    Accept a single JSON object or a list of JSON objects and insert into Supabase.
    Protected by RUN_API_KEY if set.
    """
    check_api_key(request)

    try:
        rows = payload if isinstance(payload, list) else [payload]

        # map fields to match probes table
        normalized = []
        for r in rows:
            ts = r.get("timestamp") or r.get("ts")
            host = r.get("host") or r.get("name")
            latency = r.get("avg_ms") or r.get("latency_ms")
            loss = r.get("packet_loss_pct") or r.get("loss_pct")
            protocol = (r.get("method") or r.get("protocol") or "").lower() or None

            payload_row = {
                "ts": ts,
                "host": host,
                "latency_ms": float(latency) if latency not in (None, "") else None,
                "loss_pct": float(loss) if loss not in (None, "") else None,
                "protocol": protocol,
            }

            if r.get("http_status"):  # optional
                try:
                    payload_row["http_status"] = int(r["http_status"])
                except:
                    pass
            if r.get("rtts"):
                payload_row["raw_rtts"] = r["rtts"]

            normalized.append({k: v for k, v in payload_row.items() if v is not None})

        # insert into Supabase
        url = f"{SUPABASE_URL}/rest/v1/probes"
        headers = {
            "apikey": SUPABASE_SERVICE_KEY,
            "Authorization": f"Bearer {SUPABASE_SERVICE_KEY}",
            "Content-Type": "application/json",
            "Prefer": "return=minimal"
        }
        r = requests.post(url, headers=headers, json=normalized, timeout=15)
        r.raise_for_status()
        return {"inserted": len(normalized)}

    except requests.HTTPError as e:
        # include Supabase response body in the error for easier debugging
        body = getattr(e.response, "text", str(e))
        raise HTTPException(status_code=500, detail=f"Supabase error: {body}")
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
