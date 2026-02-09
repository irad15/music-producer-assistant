import os
from openai import OpenAI
from dotenv import load_dotenv

load_dotenv()

def test_openai():
    api_key = os.getenv("OPENAI_API_KEY")
    if not api_key:
        print("❌ Error: OPENAI_API_KEY not found in .env")
        return

    try:
        client = OpenAI(api_key=api_key)
        response = client.chat.completions.create(
            model="gpt-4o-mini",
            messages=[
                {"role": "user", "content": "Hello! Reply with 'Connect Successful'."}
            ]
        )
        content = response.choices[0].message.content
        print(f"✅ OpenAI Check: {content}")
    except Exception as e:
        print(f"❌ OpenAI Error: {e}")

if __name__ == "__main__":
    test_openai()
