"""
tools/studio_knowledge.py: Studio Configuration Logic

Purpose:
- Acts as a "Lite RAG" knowledge base.
- Reads `studio_config.json` to provide services, prices, and rules to the Agent.
- Validates service types to prevent hallucinations.
"""
import json
import os

CONFIG_PATH = "config/studio_config.json"

def get_studio_config():
    """Reads the studio configuration to provide services and rules."""
    if not os.path.exists(CONFIG_PATH):
        return {"error": "Studio config not found"}
    
    with open(CONFIG_PATH, "r") as f:
        return json.load(f)

def validate_service(service_name: str) -> bool:
    """Checks if a service exists in the config."""
    config = get_studio_config()
    if "error" in config:
        return False
    return service_name.lower() in [s.lower() for s in config.get("services", {}).keys()]

def get_service_details(service_name: str):
    """Returns details for a specific service."""
    config = get_studio_config()
    if "error" in config:
        return None
    if service_name.lower() == "all":
        return config.get("services", {})
    return config.get("services", {}).get(service_name.lower())

def get_requirements():
    """Returns the list of requirements for a lead."""
    config = get_studio_config()
    if "error" in config:
        return []
    return config.get("requirements", [])
