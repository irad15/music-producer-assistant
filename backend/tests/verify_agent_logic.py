"""
verify_agent_logic.py: Agent Verification Script

Purpose:
- Manually tests the Agent Logic flow without the Frontend.
- Simulates User inputs and state transitions.
- Validates that the Graph steps through Intake -> Scoping -> Finalize.
"""
import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from langgraph.checkpoint.memory import MemorySaver
from app.agent import app_workflow, create_project_spec_model

def run_verification():
    print("🧪 Starting Agent Verification (With Memory)...")
    checkpointer = MemorySaver()
    app = app_workflow.compile(checkpointer=checkpointer)
    
    # Config for thread
    config = {"configurable": {"thread_id": "verify_thread_1"}}
    
    # 1. Start Conversation
    # Create empty spec dict
    ProjectSpec = create_project_spec_model()
    empty_spec = {k: None for k in ProjectSpec.model_fields.keys()}
    empty_spec['client_name'] = "Test User" # Partial
    
    initial_state = {
        "messages": ["Hi, I want to book a session"], 
        "project_spec": empty_spec, 
        "next_step": "intake"
    }
    
    print("\n--- Turn 1: Intake (Partial) ---")
    # Run until it stops (it won't stop automatically unless we interrupt)
    for event in app.stream(initial_state, config=config, stream_mode="values"):
        if "messages" in event:
            print(f"Agent: {event['messages'][-1]}")
            # If the agent asks a question, we break to simulate user input
            if event['next_step'] == 'intake':
                break
    
    # 2. User simulates response
    print("\n--- Turn 2: User Input (Complete Info) ---")
    # We update the state with the user's info to simulate successful extraction
    new_spec = empty_spec.copy()
    new_spec.update({
        "client_name": "Test User",
        "service_type": "mixing",
        "attendee_count": 2,
        "requested_slot": "2026-02-08T14:30:00"
    })
    
    # Update state and continue
    app.update_state(config, {"project_spec": new_spec, "messages": ["Mixing, 2 people, Sunday 2:30pm"]})
    
    # Run again - should transition to Scoping -> Finalize
    print("--- Resuming Graph ---")
    for event in app.stream(None, config=config, stream_mode="values"):
        if "messages" in event:
            print(f"Agent/Node Output: {event['messages'][-1]}")
            if event.get("next_step") == "END":
                print("✅ Reached END state.")
                break

if __name__ == "__main__":
    run_verification()
