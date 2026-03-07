import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from tools.studio_knowledge import get_studio_config, get_service_details, validate_service

def test_multi_config():
    print("🧪 Testing Multi-Studio Configuration...")

    # 1. Test Default (Backwards Compatibility)
    print("\n1. Testing Default (producer_one)...")
    config = get_studio_config()
    if config.get("timezone") == "Asia/Jerusalem":
        print("✅ Default loaded correctly (producer_one)")
    else:
        print(f"❌ Default failed: {config.get('timezone')}")

    # 2. Test Specific Config (Techno Bunker)
    print("\n2. Testing Techno Bunker...")
    config = get_studio_config("techno_bunker")
    if config.get("timezone") == "Europe/Berlin":
        print("✅ Techno Bunker loaded correctly")
    else:
        print(f"❌ Techno Bunker failed: {config.get('timezone')}")

    # 3. Test Service Details (Techno Pricing)
    print("\n3. Testing Service Details (Techno Mixing)...")
    details = get_service_details("mixing", "techno_bunker")
    if details and details["base_price"] == 600:
        print("✅ Techno Mixing price correct (600)")
    else:
        print(f"❌ Techno Mixing price incorrect: {details}")

    # 4. Test Service Details (Jazz Cat Recording)
    print("\n4. Testing Service Details (Jazz Cat Recording)...")
    details = get_service_details("recording", "jazz_cat")
    if details and details["base_price"] == 800:
        print("✅ Jazz Cat Recording price correct (800)")
    else:
        print(f"❌ Jazz Cat Recording price incorrect: {details}")

    # 5. Test Invalid ID Fallback
    print("\n5. Testing Invalid ID Fallback...")
    config = get_studio_config("non_existent_studio")
    if config.get("timezone") == "Asia/Jerusalem":
        print("✅ Fallback to producer_one working")
    else:
        print(f"❌ Fallback failed: {config.get('timezone')}")

if __name__ == "__main__":
    test_multi_config()
