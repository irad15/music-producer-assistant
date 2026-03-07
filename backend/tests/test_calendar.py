import sys
import os

# Add project root to sys.path so we can import tools directory
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from tools.calendar_mcp import get_calendar_service
from googleapiclient.errors import HttpError
import datetime

def test_calendar():
    print("🧪 Testing Google Calendar Integration...")
    
    try:
        service = get_calendar_service()
    except Exception as e:
        print(f"❌ Calendar Authentication Failed: {e}")
        print("\n💡 It looks like you haven't authenticated yet or your token has expired.")
        print("   Please run the setup script to generate a new valid token:")
        print("   👉 uv run auth/setup_auth.py 👈")
        return

    try:
        # Call the Calendar API
        now = datetime.datetime.now(datetime.timezone.utc).isoformat()
        print("📅 Fetching the next upcoming event...")
        events_result = (
            service.events()
            .list(
                calendarId="primary",
                timeMin=now,
                maxResults=1,
                singleEvents=True,
                orderBy="startTime",
            )
            .execute()
        )
        events = events_result.get("items", [])

        if not events:
            print("✅ Calendar Auth Success (No upcoming events found in primary calendar)")
        else:
            for event in events:
                start = event["start"].get("dateTime", event["start"].get("date"))
                print(f"✅ Calendar Auth Success! Next event: {start} - {event['summary']}")

    except HttpError as error:
        print(f"❌ Calendar API call failed: {error}")

if __name__ == "__main__":
    test_calendar()
