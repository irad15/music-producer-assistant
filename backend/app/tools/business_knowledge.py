import json
import os
from typing import Optional, Dict, Any

DEFAULT_CONFIG = "app/config/producer_one.json"

# --- MAIN SERVICE LOGIC ---

def validate_service(service_name: str, business_id: str = "producer_one") -> bool:
    """Checks if a service exists in the config."""
    config = get_business_config(business_id)
    if "error" in config:
        return False
    return service_name.lower() in [s.lower() for s in config.get("services", {}).keys()]

def get_service_details(service_name: str, business_id: str = "producer_one"):
    """Returns details for a specific service."""
    config = get_business_config(business_id)
    if "error" in config:
        return None
    if service_name.lower() == "all":
        return config.get("services", {})
    
    # Returns the full dictionary for the service (includes duration, base_price, etc.)
    return config.get("services", {}).get(service_name.lower())

def get_requirements(business_id: str = "producer_one"):
    """Returns the list of requirements for a lead."""
    config = get_business_config(business_id)
    if "error" in config:
        return []
    return config.get("requirements", [])


# --- HELPER FUNCTIONS ---

def get_business_config(business_id: str = "producer_one") -> Dict[str, Any]:
    """
    Reads the business configuration for a specific business_id.
    Defaults to 'producer_one' if not found or not specified.
    """
    path = f"app/config/{business_id}.json"
    
    # Fallback to default if specific file doesn't exist
    if not os.path.exists(path):
        print(f"⚠️ Config '{path}' not found. Falling back to default.")
        path = DEFAULT_CONFIG
        
    if not os.path.exists(path):
        return {"error": "business config not found"}
    
    try:
        # Attempt to open and parse the JSON configuration file
        with open(path, "r") as f:
            return json.load(f)
    except json.JSONDecodeError:
        # Handle cases where the JSON file is malformed
        return {"error": "Invalid JSON in config file"}
