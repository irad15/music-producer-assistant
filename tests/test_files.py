import os
import json

TEMP_FILE = ".tmp/test_write.txt"
CONFIG_FILE = "config/studio_config.json"
LEADS_FILE = "data/leads.json"

def test_files():
    # 1. Test .tmp write/read
    os.makedirs(os.path.dirname(TEMP_FILE), exist_ok=True)
    try:
        with open(TEMP_FILE, "w") as f:
            f.write("test")
        with open(TEMP_FILE, "r") as f:
            content = f.read()
        if content == "test":
            print("✅ .tmp Write/Read Successful")
        else:
            print("❌ .tmp Write/Read Failed")
    except Exception as e:
        print(f"❌ .tmp Error: {e}")
    finally:
        if os.path.exists(TEMP_FILE):
            os.remove(TEMP_FILE)

    # 2. Check Service Files
    if os.path.exists(CONFIG_FILE):
        print(f"✅ Found {CONFIG_FILE}")
    else:
        print(f"⚠️  Missing {CONFIG_FILE} (Will need to create)")

    if os.path.exists(LEADS_FILE):
        print(f"✅ Found {LEADS_FILE}")
    else:
        print(f"⚠️  Missing {LEADS_FILE} (Will need to create)")

if __name__ == "__main__":
    test_files()
