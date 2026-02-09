import os
import resend
from dotenv import load_dotenv

load_dotenv()

def test_resend():
    api_key = os.getenv("RESEND_API_KEY")
    if not api_key:
        print("❌ Error: RESEND_API_KEY not found in .env")
        return

    resend.api_key = api_key

    try:
        r = resend.Emails.send({
            "from": "onboarding@resend.dev",
            "to": "iradyaacoby@gmail.com",
            "subject": "Groove Handshake",
            "html": "<p>Link Verified ✅</p>"
        })
        print(f"✅ Resend Check: Email sent! ID: {r['id']}")
    except Exception as e:
        print(f"❌ Resend Error: {e}")

if __name__ == "__main__":
    test_resend()
