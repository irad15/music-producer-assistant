"""
agent/graph.py: Graph Compilation

Builds and exports the StateGraph workflow.
The checkpointer is attached at runtime in api.py.
"""
from langgraph.graph import StateGraph, END

from app.agent.state import AgentState
from app.agent.nodes import intake_node, scoping_node, finalize_node
from app.agent.edges import route_after_intake, route_after_scoping


workflow = StateGraph(AgentState)

workflow.add_node("intake", intake_node)
workflow.add_node("scoping", scoping_node)
workflow.add_node("finalize", finalize_node)

workflow.set_entry_point("intake")

workflow.add_conditional_edges(
    "intake",
    route_after_intake,
    {
        "intake": "intake",    # Loop until all fields collected
        "scoping": "scoping",
    }
)

workflow.add_conditional_edges(
    "scoping",
    route_after_scoping,
    {
        "intake": "intake",    # Slot rejected — go back
        "finalize": "finalize",
    }
)

workflow.add_edge("finalize", END)

# Export the uncompiled workflow (checkpointer is attached in api.py)
app_workflow = workflow
