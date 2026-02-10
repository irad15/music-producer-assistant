"""
tools/calendar_mcp.py: Google Calendar Integration (Refactored)
"""
import os
import datetime
import json
from zoneinfo import ZoneInfo
from google.oauth2.credentials import Credentials
from googleapiclient.discovery import build
from google.auth.transport.requests import Request
from tools.studio_knowledge import get_studio_config

SCOPES = ["https://www.googleapis.com/auth/calendar.readonly"]

def get_calendar_service():
    """Authenticated and returns the Google Calendar service."""
    creds = None
    paths = ["auth/token.json", "/etc/secrets/token.json"]
    
    # 1. Check Files
    for path in paths:
        if os.path.exists(path):
            creds = Credentials.from_authorized_user_file(path, SCOPES)
            break
            
    # 2. Check Env Var
    if not creds and os.environ.get("GOOGLE_TOKEN_JSON"):
        token_info = json.loads(os.environ["GOOGLE_TOKEN_JSON"])
        creds = Credentials.from_authorized_user_info(token_info, SCOPES)

    # 3. Validation / Refresh
    if not creds or not creds.valid:
        if creds and creds.expired and creds.refresh_token:
            creds.refresh(Request())
        else:
            raise Exception("Token invalid/missing. Check auth/token.json or GOOGLE_TOKEN_JSON.")
            
    return build("calendar", "v3", credentials=creds)

def parse_time(iso_str: str, tz_name: str) -> datetime.datetime:
    """Parses time string and ensures timezone awareness."""
    try:
        dt = datetime.datetime.fromisoformat(iso_str)
    except ValueError:
        dt = datetime.datetime.strptime(iso_str, "%Y-%m-%d %H:%M")
    
    tz = ZoneInfo(tz_name) if tz_name != "UTC" else datetime.timezone.utc
    if dt.tzinfo is None:
        return dt.replace(tzinfo=tz)
    return dt.astimezone(tz)

def is_busy(service, start: datetime.datetime, end: datetime.datetime):
    """Checks if a specific slot has events."""
    events = service.events().list(
        calendarId="primary", timeMin=start.isoformat(), timeMax=end.isoformat(), singleEvents=True
    ).execute()
    return bool(events.get("items", []))

def check_availability(start_time_iso: str, duration_hours: int):
    """Checks slot availability and finds alternatives if busy."""
    service = get_calendar_service()
    studio_tz = get_studio_config().get("timezone", "UTC")
    
    # Parse & Calc End
    try:
        start_dt = parse_time(start_time_iso, studio_tz)
    except Exception as e:
        return {"available": False, "error": f"Date error: {e}"}
        
    end_dt = start_dt + datetime.timedelta(hours=duration_hours)
    print(f"📅 Checking Availability: {start_dt.isoformat()} to {end_dt.isoformat()} ({studio_tz})")

    # Check Primary Slot
    if not is_busy(service, start_dt, end_dt):
        return {"available": True}

    # Find 3 Alternatives
    alternatives = []
    search_start = end_dt
    while len(alternatives) < 3:
        search_start += datetime.timedelta(hours=1)
        search_end = search_start + datetime.timedelta(hours=duration_hours)
        
        if not is_busy(service, search_start, search_end):
            alternatives.append(search_start.isoformat())
            
    return {"available": False, "alternatives": alternatives}
