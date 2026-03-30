from fastapi import FastAPI, Request, Query
from fastapi.responses import Response, JSONResponse
from datetime import datetime
import base64
import json
import os
import traceback
import uuid

from dotenv import load_dotenv
import gspread
import httpx
from google.oauth2.service_account import Credentials

# Load environment variables from the .env file in the same folder
load_dotenv()

# Create the FastAPI app
app = FastAPI()

# 1x1 transparent PNG image encoded in base64
TRANSPARENT_PIXEL_B64 = (
    "iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAYAAAAfFcSJAAAADUlEQVR42mNkYPhf"
    "DwAChwGA60e6kgAAAABJRU5ErkJggg=="
)
TRANSPARENT_PIXEL = base64.b64decode(TRANSPARENT_PIXEL_B64)

# Environment variables
SHEET_ID = os.getenv("SHEET_ID")
GA4_MEASUREMENT_ID = os.getenv("GA4_MEASUREMENT_ID")
GA4_API_SECRET = os.getenv("GA4_API_SECRET")
ENVIRONMENT = os.getenv("ENVIRONMENT", "development")

# Google Sheets scopes
SCOPES = ["https://www.googleapis.com/auth/spreadsheets"]

# --- Cached Google Sheets client for connection reuse ---
_cached_gspread_client = None


def get_credentials():
    """Load Google service account credentials from base64 env var or local file."""
    b64 = os.getenv("GOOGLE_CREDENTIALS_B64")
    if b64:
        json_data = base64.b64decode(b64).decode("utf-8")
        info = json.loads(json_data)
        return Credentials.from_service_account_info(info, scopes=SCOPES)
    secret_path = "/etc/secrets/credentials.json"
    local_path = "credentials.json"
    path = secret_path if os.path.exists(secret_path) else local_path
    return Credentials.from_service_account_file(path, scopes=SCOPES)


def get_gspread_client():
    """Return a cached gspread client, creating one if needed."""
    global _cached_gspread_client
    if _cached_gspread_client is None:
        creds = get_credentials()
        _cached_gspread_client = gspread.authorize(creds)
    return _cached_gspread_client


def get_sheet():
    """Connect to Google Sheets and return the first worksheet."""
    client = get_gspread_client()
    spreadsheet = client.open_by_key(SHEET_ID)
    return spreadsheet.get_worksheet(0)


def check_duplicate(sheet, email: str, current_date: str) -> bool:
    """Check if this email already has a row for today. Returns True if duplicate found."""
    if email == "unknown":
        return False
    try:
        all_rows = sheet.get_all_values()
        for row in all_rows:
            # row format: [Date, Time, Email, User Agent]
            if len(row) >= 3 and row[0] == current_date and row[2] == email:
                return True
    except Exception as e:
        print(f"Dedup check failed: {e}", flush=True)
    return False


@app.on_event("startup")
def startup_check():
    """Runs once when the server starts — confirms SHEET_ID and credentials are working."""
    print("=== STARTUP CHECK ===", flush=True)
    print(f"SHEET_ID loaded: {SHEET_ID}", flush=True)
    print(f"ENVIRONMENT: {ENVIRONMENT}", flush=True)
    print("GOOGLE_CREDENTIALS_B64 present:", bool(os.getenv("GOOGLE_CREDENTIALS_B64")), flush=True)

    try:
        client = get_gspread_client()
        spreadsheet = client.open_by_key(SHEET_ID)
        print(f"Connected to spreadsheet: '{spreadsheet.title}'", flush=True)
        print("Startup check PASSED — Google Sheets connection is working.", flush=True)
    except Exception as e:
        print(f"Startup check FAILED: {e}", flush=True)
        print(traceback.format_exc(), flush=True)

    if ENVIRONMENT == "development":
        print("DEV MODE - GA4 disabled", flush=True)
    else:
        print("PROD MODE - GA4 enabled", flush=True)

    print("=====================", flush=True)


@app.get("/")
def root():
    return {"status": "ok", "environment": ENVIRONMENT}


@app.get("/test-sheets")
def test_sheets():
    """Debug endpoint — tries to append a test row and reports success or failure."""
    try:
        sheet = get_sheet()
        sheet.append_row(["TEST", "TEST", "TEST", "TEST"])
        print("Test row appended successfully.", flush=True)
        return JSONResponse({"success": True})
    except Exception as e:
        error_msg = traceback.format_exc()
        print(f"Test row failed: {e}", flush=True)
        print(error_msg, flush=True)
        return JSONResponse({"success": False, "error": str(e)})


async def send_ga4_event(
    client_id: str,
    email: str,
    current_date: str,
    current_time: str,
    user_agent: str,
):
    """Send an email_open event to GA4 via Measurement Protocol with 5s timeout."""
    if ENVIRONMENT == "development":
        print("DEV MODE - GA4 disabled", flush=True)
        return

    print("PROD MODE - GA4 enabled", flush=True)

    try:
        url = (
            f"https://www.google-analytics.com/mp/collect"
            f"?measurement_id={GA4_MEASUREMENT_ID}&api_secret={GA4_API_SECRET}"
        )
        payload = {
            "client_id": client_id,
            "events": [
                {
                    "name": "email_open",
                    "params": {
                        "subscriber_email": email,
                        "date": current_date,
                        "time": current_time,
                        "user_agent": user_agent,
                    },
                }
            ],
        }
        async with httpx.AsyncClient(timeout=5.0) as http_client:
            response = await http_client.post(url, json=payload)
        print(f"GA4 event sent successfully (status {response.status_code}).", flush=True)
    except Exception as e:
        print(f"Failed to send GA4 event: {e}", flush=True)
        print(traceback.format_exc(), flush=True)


@app.get("/track")
async def track(
    request: Request,
    email: str = Query(default=None),
    uid: str = Query(default=None),
):
    now = datetime.now()
    current_date = now.strftime("%Y-%m-%d")
    current_time = now.strftime("%H:%M:%S")
    user_agent = request.headers.get("user-agent", "Unknown")

    # Determine subscriber email and GA4 client_id
    subscriber_email = email if email else "unknown"
    client_id = email if email else str(uuid.uuid4())

    print(f"[{current_date} {current_time}] Email opened | email={subscriber_email} | uid={uid} | UA: {user_agent}", flush=True)

    # --- Google Sheets: deduplication + save ---
    is_duplicate = False
    try:
        sheet = get_sheet()
        is_duplicate = check_duplicate(sheet, subscriber_email, current_date)

        if is_duplicate:
            print(f"Duplicate detected for {subscriber_email} on {current_date} — skipping.", flush=True)
        else:
            sheet.append_row([current_date, current_time, subscriber_email, user_agent])
            print("Row saved to Google Sheets successfully.", flush=True)
    except Exception as e:
        print(f"Failed to save to Google Sheets: {e}", flush=True)
        print(traceback.format_exc(), flush=True)

    # --- GA4: only send if not a duplicate ---
    if not is_duplicate:
        await send_ga4_event(client_id, subscriber_email, current_date, current_time, user_agent)

    return Response(content=TRANSPARENT_PIXEL, media_type="image/png")
