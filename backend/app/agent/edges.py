"""
agent/edges.py: Edges & Routers

Each function inspects the current state and returns the name of the next node.
Routing logic lives here — nodes only update state, they never decide where to go next.
"""
from app.agent.state import AgentState
from app.tools.studio_knowledge import get_requirements


def route_after_intake(state: AgentState) -> str:
    """
    Routes after intake_node.
    Goes to 'scoping' only when all required fields are collected,
    otherwise loops back to 'intake' to keep asking.
    """
    spec = state['project_spec']
    required_ids = [req['id'] for req in get_requirements()]
    all_collected = all(spec.get(field) is not None for field in required_ids)
    return "scoping" if all_collected else "intake"


def route_after_scoping(state: AgentState) -> str:
    """
    Routes after scoping_node.
    If the slot is still set, it was available → go to 'finalize'.
    If it was cleared to None, the slot was busy → go back to 'intake'.
    """
    slot = state['project_spec'].get('requested_slot')
    return "finalize" if slot is not None else "intake"
