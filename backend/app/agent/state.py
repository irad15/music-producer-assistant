"""
agent/state.py: State & Schema Definitions

- Defines the AgentState TypedDict used across all nodes.
- Dynamically builds the ProjectSpec Pydantic model from studio_config.json.
"""
from typing import TypedDict, Optional, List, Dict, Any
from pydantic import create_model, Field
from app.tools.studio_knowledge import get_requirements


def create_project_spec_model():
    """
    Dynamically creates a Pydantic model based on studio_config.json requirements.
    """
    fields = {}
    for req in get_requirements():
        field_type = str if req['type'] == 'string' else int
        fields[req['id']] = (Optional[field_type], Field(None, description=req['description']))

    # Internal field — always present
    fields['producer_summary'] = (Optional[str], Field(None, description="Final summary text"))

    return create_model('ProjectSpec', **fields)


# Initialize the dynamic model at module load time
ProjectSpec = create_project_spec_model()


class AgentState(TypedDict):
    messages: List[str]           # Manual append
    project_spec: Dict[str, Any]  # Dict because the model is dynamic
