import os
from fastapi import FastAPI, BackgroundTasks, HTTPException
from fastapi.responses import JSONResponse
from fastapi.middleware.cors import CORSMiddleware
import requests

# Import probe runner
from probe import run_probe_once

SUPABASE_URL = os.getenv("SUPABASE_URL")
SUPABASE_SERVICE_KEY = os.getenv("SUPABASE_SERVICE_KEY")
SUPABASE_ANON_KEY = os.getenv("SUPABASE_ANON_KEY")  # for read if you prefer anon

if not SUPABASE_URL or not SUPABASE_SERVICE_KEY:
    raise SystemExit("SUPABASE_URL and SUPABASE_SERVICE_KEY must be set")

app = FastAPI(title="Probe API")

# allow requests from your Streamlit app origin; for testing you may use "*" then lock down later
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

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
async def run_probe(background_tasks: BackgroundTasks, host: str = "1.1.1.1"):
    """
    Trigger a single probe in the background. Use POST /run?host=example.com
    """
    # Optionally protect this endpoint by checking a header or env token (omitted here)
    background_tasks.add_task(background_probe_task, host)
    return JSONResponse({"status": "started", "host": host})

@app.get("/data")
async def get_data(limit: int = 50):
    try:
        data = fetch_data_from_supabase(limit)
        return {"count": len(data), "data": data}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
