import os
import logging
from datetime import datetime
import gspread
from google.oauth2.service_account import Credentials
from dotenv import load_dotenv

load_dotenv()
logger = logging.getLogger("atlas.sheets_engine")

GOOGLE_APPLICATION_CREDENTIALS = os.getenv("GOOGLE_APPLICATION_CREDENTIALS")
GOOGLE_SHEET_ID = os.getenv("GOOGLE_SHEET_ID")

def append_lead_to_sheet(name: str, contact: str, intent: str, business_id: str = "default") -> dict:
    """
    Appends a new lead row to the specified Google Sheet.
    """
    if not GOOGLE_APPLICATION_CREDENTIALS or not GOOGLE_SHEET_ID:
        error_msg = "Google Sheets credentials or Sheet ID not configured in .env."
        logger.error(f"[sheets_engine] {error_msg}")
        return {"success": False, "message": error_msg}
        
    try:
        if not os.path.exists(GOOGLE_APPLICATION_CREDENTIALS):
            error_msg = f"Credentials file not found at path: {GOOGLE_APPLICATION_CREDENTIALS}"
            logger.error(f"[sheets_engine] {error_msg}")
            return {"success": False, "message": error_msg}

        scopes = ["https://www.googleapis.com/auth/spreadsheets"]
        creds = Credentials.from_service_account_file(GOOGLE_APPLICATION_CREDENTIALS, scopes=scopes)
        client = gspread.authorize(creds)
        
        sheet = client.open_by_key(GOOGLE_SHEET_ID).sheet1
        
        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        row = [timestamp, business_id, name, contact, intent]
        
        sheet.append_row(row)
        
        logger.info(f"[sheets_engine] Successfully appended lead {name} to sheet.")
        return {"success": True, "message": f"Lead '{name}' added successfully."}
        
    except Exception as e:
        logger.error(f"[sheets_engine] Error appending lead to sheet: {e}")
        return {"success": False, "message": f"Error: {str(e)}"}
