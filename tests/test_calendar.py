import os
import datetime
from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow
from googleapiclient.discovery import build
from googleapiclient.errors import HttpError

# If modifying these scopes, delete the file token.json
SCOPES = ["https://www.googleapis.com/auth/calendar.readonly"]

def test_calendar():
    creds = None
    # The file token.json stores the user's access and refresh tokens, and is
    # created automatically when the authorization flow completes for the first
    # time.
    if os.path.exists("auth/token.json"):
        creds = Credentials.from_authorized_user_file("auth/token.json", SCOPES)
    # If there are no (valid) credentials available, let the user log in.
    if not creds or not creds.valid:
        if creds and creds.expired and creds.refresh_token:
            print("🔄 Refreshing Token...")
            creds.refresh(Request())
        else:
            if not os.path.exists("auth/credentials.json"):
                print("❌ Error: auth/credentials.json not found for Google Calendar")
                return
            print("⏳ Initiating OAuth Flow...")
            flow = InstalledAppFlow.from_client_secrets_file(
                "auth/credentials.json", SCOPES
            )
            creds = flow.run_local_server(port=0)
        # Save the credentials for the next run
        with open("auth/token.json", "w") as token:
            token.write(creds.to_json())

    try:
        service = build("calendar", "v3", credentials=creds)

        # Call the Calendar API
        now = datetime.datetime.now(datetime.timezone.utc).isoformat()
        print("📅 Getting the next event")
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
            print("✅ Calendar Auth Success (No upcoming events found)")
        else:
            for event in events:
                start = event["start"].get("dateTime", event["start"].get("date"))
                print(f"✅ Calendar Auth Success! Next event: {start} - {event['summary']}")

    except HttpError as error:
        print(f"❌ An error occurred: {error}")

if __name__ == "__main__":
    test_calendar()
