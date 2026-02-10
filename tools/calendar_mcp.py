"""
tools/calendar_mcp.py: Google Calendar Integration

Purpose:
- Handles all interactions with the Google Calendar API.
- Authenticates using `token.json` (from Phase 2 handshake).
- Checks availability and finds alternative slots.
- Enforces TimeZone awareness to avoid API errors.
"""
import os
import datetime
from google.oauth2.credentials import Credentials
from googleapiclient.discovery import build
from google.auth.transport.requests import Request
from tools.studio_knowledge import get_studio_config

SCOPES = ["https://www.googleapis.com/auth/calendar.readonly"]

def get_calendar_service():
    """Authenticated and returns the Google Calendar service."""
    creds = None
    # Priority 1: Local File (Dev)
    token_path = "auth/token.json"
    if os.path.exists(token_path):
        creds = Credentials.from_authorized_user_file(token_path, SCOPES)
    
    # Priority 2: Env Var (Prod/Render)
    elif os.environ.get("GOOGLE_TOKEN_JSON"):
        import json
        token_info = json.loads(os.environ.get("GOOGLE_TOKEN_JSON"))
        creds = Credentials.from_authorized_user_info(token_info, SCOPES)

    if not creds or not creds.valid:
        if creds and creds.expired and creds.refresh_token:
            creds.refresh(Request())
        else:
            raise Exception("Token invalid or missing. Local: check auth/token.json. Prod: check GOOGLE_TOKEN_JSON env var.")
            
    return build("calendar", "v3", credentials=creds)

def check_availability(start_time_iso: str, duration_hours: int):
    """
    Checks if a slot is free.
    Returns:
        - {"available": True}
        - {"available": False, "alternatives": [list of 3 next slots]}
    """
    service = get_calendar_service()
    
    # Use Studio Timezone
    studio_tz_name = get_studio_config().get("timezone", "UTC")
    try:
        if studio_tz_name == "UTC":
             tz = datetime.timezone.utc
        else:
             from zoneinfo import ZoneInfo
             tz = ZoneInfo(studio_tz_name)
    except Exception as e:
        print(f"⚠️ Timezone error: {e}. Fallback to UTC.")
        tz = datetime.timezone.utc

    # Parse ISO. 
    # If naive (no offset), assume studio timezone.
    # If aware (has offset), convert to studio timezone.
    try:
        start_dt = datetime.datetime.fromisoformat(start_time_iso)
    except ValueError:
        # Fallback for simple "YYYY-MM-DD HH:MM"
        try:
             start_dt = datetime.datetime.strptime(start_time_iso, "%Y-%m-%d %H:%M")
        except:
             return {"available": False, "alternatives": [], "error": "Invalid date format"}

    if start_dt.tzinfo is None:
        start_dt = start_dt.replace(tzinfo=tz)
    else:
        start_dt = start_dt.astimezone(tz)
        
    end_dt = start_dt + datetime.timedelta(hours=duration_hours)
    
    print(f"📅 Checking Availability: {start_dt.isoformat()} to {end_dt.isoformat()} ({studio_tz_name})")
    
    # Check for conflicts
    events_result = service.events().list(
        calendarId="primary",
        timeMin=start_dt.isoformat(),
        timeMax=end_dt.isoformat(),
        singleEvents=True
    ).execute()
    
    if not events_result.get("items", []):
        return {"available": True}
    
    # If busy, find next 3 slots
    alternatives = []
    search_start = end_dt
    
    while len(alternatives) < 3:
        # Simple heuristic: Check next hour, 9am-8pm window
        # For MVP: just check strictly hour-by-hour forward for now, respecting sleep time?
        # Let's keep it simple: just look ahead in 1 hour increments
        search_start += datetime.timedelta(hours=1)
        search_end = search_start + datetime.timedelta(hours=duration_hours)
        
        # very basic check
        events = service.events().list(
            calendarId="primary",
            timeMin=search_start.isoformat(),
            timeMax=search_end.isoformat(),
            singleEvents=True
        ).execute()
        
        if not events.get("items", []):
            alternatives.append(search_start.isoformat())
            
    return {"available": False, "alternatives": alternatives}
