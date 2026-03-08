import os
from google_auth_oauthlib.flow import InstalledAppFlow
from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials

# Scopes required for the application
SCOPES = ["https://www.googleapis.com/auth/calendar.readonly"]

def setup_authentication():
    """
    Handles the Google OAuth 2.0 flow to explicitly generate and save 
    a user's `token.json`.
    """
    print("🚀 Starting Google Calendar Authentication Setup...")

    # Ensure we are running from the project root by checking for the `auth` directory
    if not os.path.exists("app/auth"):
        print("❌ Error: 'app/auth' directory not found. Please run this script from the root of the project: `uv run app/auth/setup_auth.py`")
        return

    # Check for credentials
    if not os.path.exists("app/auth/credentials.json"):
        print("❌ Error: 'app/auth/credentials.json' not found.")
        print("   Please download your OAuth client ID from the Google Cloud Console")
        print("   and save it as 'app/auth/credentials.json' before running this script.")
        return

    creds = None

    # Check if a token already exists
    if os.path.exists("app/auth/token.json"):
        print("ℹ️ An existing `app/auth/token.json` was found. Validating...")
        try:
            creds = Credentials.from_authorized_user_file("app/auth/token.json", SCOPES)
            
            if creds and creds.valid:
                print("✅ Your existing token is still valid. No action required!")
                return
                
            if creds and creds.expired and creds.refresh_token:
                print("🔄 Existing token expired. Attempting to refresh...")
                try:
                    creds.refresh(Request())
                    print("✅ Token refreshed successfully!")
                except Exception as e:
                    print(f"⚠️ Token refresh failed: {e}")
                    creds = None # Force complete re-auth
        except Exception as e:
            print(f"⚠️ Failed to load existing token: {e}")
            creds = None
            
    # Initiate the interactive OAuth flow
    if not creds or not creds.valid:
        print("⏳ Initiating Google OAuth Login Flow in your browser...")
        try:
            flow = InstalledAppFlow.from_client_secrets_file(
                "app/auth/credentials.json", SCOPES
            )
            # Run local server to capture the callback
            creds = flow.run_local_server(port=0)
            print("✅ Successfully authenticated with Google!")
        except Exception as e:
            print(f"❌ Authentication flow failed: {e}")
            return
            
    # Save the successful credentials
    print("💾 Saving your new token...")
    try:
        with open("app/auth/token.json", "w") as token:
            token.write(creds.to_json())
        print("✅ Success! Your `token.json` is ready in the `app/auth/` directory.")
        print("   You may now run `uv run tests/test_calendar.py` to test it.")
    except Exception as e:
        print(f"❌ Failed to save token: {e}")

if __name__ == "__main__":
    setup_authentication()
