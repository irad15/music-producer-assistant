import json
import os
from typing import Optional, Dict, Any

DEFAULT_CONFIG = "config/producer_one.json"

def get_studio_config(studio_id: str = "producer_one") -> Dict[str, Any]:
    """
    Reads the studio configuration for a specific studio_id.
    Defaults to 'producer_one' if not found or not specified.
    """
    path = f"config/{studio_id}.json"
    
    # Fallback to default if specific file doesn't exist
    if not os.path.exists(path):
        print(f"⚠️ Config '{path}' not found. Falling back to default.")
        path = DEFAULT_CONFIG
        
    if not os.path.exists(path):
        return {"error": "Studio config not found"}
    
    try:
        with open(path, "r") as f:
            return json.load(f)
    except json.JSONDecodeError:
        return {"error": "Invalid JSON in config file"}

def validate_service(service_name: str, studio_id: str = "producer_one") -> bool:
    """Checks if a service exists in the config."""
    config = get_studio_config(studio_id)
    if "error" in config:
        return False
    return service_name.lower() in [s.lower() for s in config.get("services", {}).keys()]

def get_service_details(service_name: str, studio_id: str = "producer_one"):
    """Returns details for a specific service."""
    config = get_studio_config(studio_id)
    if "error" in config:
        return None
    if service_name.lower() == "all":
        return config.get("services", {})
    return config.get("services", {}).get(service_name.lower())

def get_requirements(studio_id: str = "producer_one"):
    """Returns the list of requirements for a lead."""
    config = get_studio_config(studio_id)
    if "error" in config:
        return []
    return config.get("requirements", [])
