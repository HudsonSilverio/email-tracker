from fastapi import FastAPI, Request
from fastapi.responses import Response, JSONResponse
from datetime import datetime
import base64
import os
import traceback

from dotenv import load_dotenv
import gspread
from google.oauth2.service_account import Credentials

# Load environment variables from the .env file in the same folder
load_dotenv()

# Create the FastAPI app
app = FastAPI()

# 1x1 transparent PNG image encoded in base64
# This is a minimal valid PNG file (smallest possible)
TRANSPARENT_PIXEL_B64 = (
    "iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAYAAAAfFcSJAAAADUlEQVR42mNkYPhf"
    "DwAChwGA60e6kgAAAABJRU5ErkJggg=="
)

# Decode the base64 string into raw bytes once at startup
TRANSPARENT_PIXEL = base64.b64decode(TRANSPARENT_PIXEL_B64)

# The Google Sheets ID comes from an environment variable
# Example: export SHEET_ID=1BxiMVs0XRA5nFMdKvBdBZjgmUUqptlbs74OgVE2upms
SHEET_ID = os.getenv("SHEET_ID")

# The scopes define what permissions we are requesting from Google
SCOPES = ["https://www.googleapis.com/auth/spreadsheets"]


def get_sheet():
    """Connect to Google Sheets and return the first worksheet."""
    # Load the service account credentials from the local credentials.json file
    creds = Credentials.from_service_account_file("credentials.json", scopes=SCOPES)

    # Authorize the gspread client with those credentials
    client = gspread.authorize(creds)

    # Open the spreadsheet by its ID and return the first sheet (index 0)
    spreadsheet = client.open_by_key(SHEET_ID)
    return spreadsheet.get_worksheet(0)


@app.on_event("startup")
def startup_check():
    """Runs once when the server starts — confirms SHEET_ID and credentials are working."""
    print("=== STARTUP CHECK ===", flush=True)
    print(f"SHEET_ID loaded: {SHEET_ID}", flush=True)

    # Test the connection to Google Sheets
    try:
        creds = Credentials.from_service_account_file("credentials.json", scopes=SCOPES)
        client = gspread.authorize(creds)
        spreadsheet = client.open_by_key(SHEET_ID)
        print(f"Connected to spreadsheet: '{spreadsheet.title}'", flush=True)
        print("Startup check PASSED — Google Sheets connection is working.", flush=True)
    except Exception as e:
        print(f"Startup check FAILED: {e}", flush=True)
        print(traceback.format_exc(), flush=True)

    print("=====================", flush=True)


@app.get("/")
def root():
    # Simple health-check endpoint
    return {"status": "ok"}


@app.get("/test-sheets")
def test_sheets():
    """Debug endpoint — tries to append a test row and reports success or failure."""
    try:
        sheet = get_sheet()
        sheet.append_row(["TEST", "TEST", "TEST"])
        print("Test row appended successfully.", flush=True)
        return JSONResponse({"success": True})
    except Exception as e:
        error_msg = traceback.format_exc()
        print(f"Test row failed: {e}", flush=True)
        print(error_msg, flush=True)
        return JSONResponse({"success": False, "error": str(e)})


@app.get("/track")
def track(request: Request):
    # Get the current date and time, split into separate values for spreadsheet columns
    now = datetime.now()
    current_date = now.strftime("%Y-%m-%d")   # e.g. 2024-03-15
    current_time = now.strftime("%H:%M:%S")   # e.g. 14:32:07

    # Get the User-Agent header sent by the email client
    user_agent = request.headers.get("user-agent", "Unknown")

    # Print the tracking info to the console (useful for debugging)
    print(f"[{current_date} {current_time}] Email opened | User-Agent: {user_agent}", flush=True)

    # Try to save the tracking data to Google Sheets
    try:
        # Get the first worksheet from the spreadsheet
        sheet = get_sheet()

        # Append a new row with: date, time, and user-agent
        sheet.append_row([current_date, current_time, user_agent])

        print("Row saved to Google Sheets successfully.", flush=True)

    except Exception as e:
        # If anything goes wrong (no internet, wrong ID, missing file, etc.)
        # we log the error but DO NOT crash — the pixel image must always be returned
        print(f"Failed to save to Google Sheets: {e}", flush=True)
        print(traceback.format_exc(), flush=True)

    # Return the transparent 1x1 PNG so the email client renders nothing visible
    return Response(content=TRANSPARENT_PIXEL, media_type="image/png")
