"""
agent.py: The LangGraph Brain

Purpose:
- Defines the State Machine: Intake -> Scoping -> Finalize.
- Implements the 'Groove' persona and logic router.
- Manages the 'ProjectSpec' state object.
- Uses 'MemorySaver' to allow human-in-the-loop logic (interrupts).
"""
import os
import json
# Load Environment
from dotenv import load_dotenv, find_dotenv
load_dotenv(find_dotenv())
import datetime
from typing import TypedDict, Optional, List
from langgraph.graph import StateGraph, END
from langgraph.graph import StateGraph, END
# from langgraph.checkpoint.memory import MemorySaver (Moved to API)
from langchain_openai import ChatOpenAI
from langchain_core.messages import SystemMessage, HumanMessage
from typing import Dict, Any, List, Optional
from pydantic import create_model, Field

# Import Tools
from app.tools.studio_knowledge import get_service_details, validate_service, get_requirements
from app.tools.calendar_tool import check_availability
import resend

# ... (Environment loading) ...

# --- DYNAMIC STATE DEFINITION ---

def create_project_spec_model():
    """
    Dynamically creates a Pydantic model based on studio_config.json requirements.
    """
    requirements = get_requirements()
    fields = {}
    
    for req in requirements:
        field_type = str if req['type'] == 'string' else int
        # Field(None) makes it optional by default
        fields[req['id']] = (Optional[field_type], Field(None, description=req['description']))
    
    # Always add producer_summary as it's internal
    fields['producer_summary'] = (Optional[str], Field(None, description="Final summary text"))
    
    return create_model('ProjectSpec', **fields)

# Initialize the dynamic model
ProjectSpec = create_project_spec_model()

class AgentState(TypedDict):
    messages: List[str] # Manual Append
    project_spec: Dict[str, Any] # Now a dict, since the model is dynamic
    next_step: str

# --- NODES ---

# --- HELPER FUNCTIONS ---

def get_llm():
    api_key = os.getenv("OPENAI_API_KEY")
    if not api_key:
        print("❌ ERROR: OPENAI_API_KEY is missing")
    return ChatOpenAI(model="gpt-4o-mini", temperature=0, api_key=api_key)

def analyze_conversation(messages: List[str], current_data: Dict[str, Any]) -> Dict[str, Any]:
    """Extracts project fields from conversation history."""
    DynamicSpec = create_project_spec_model()
    req_desc = "\n".join([f"- {r['id']}: {r['description']}" for r in get_requirements()])
    
    system_prompt = f"""You are an expert data extractor. Extract these fields:
    {req_desc}
    Existing Data: {json.dumps(current_data)}
    Rules:
    - Only extract explicitly provided fields. Don't overwrite unless updated.
    - Map 'Mixing' -> service_type='mixing'.
    - Dates: Prefer DD/MM/YYYY. Naive ISO for local time.
    - If 'candidate_slot' exists and user agrees, set 'requested_slot' to it.
    """
    
    llm = get_llm().with_structured_output(DynamicSpec)
    extraction_messages = [SystemMessage(content=system_prompt)] + [HumanMessage(content=m) for m in messages[-5:]]
    
    try:
        result = llm.invoke(extraction_messages)
        return result.model_dump(exclude_unset=True, exclude_none=True)
    except Exception as e:
        print(f"⚠️ Extraction failed: {e}")
        return {}

def generate_response(messages: List[str], current_data: Dict[str, Any], missing_field: str) -> str:
    """Generates a conversational question for the next missing field."""
    system_prompt = f"""You are 'Groove', professional music producer.
    Status: {json.dumps(current_data)}
    Missing: {missing_field}
    Task: Acknowledge new info. Ask for '{missing_field}'. One question only. Short.
    """
    response_messages = [SystemMessage(content=system_prompt)] + [HumanMessage(content=m) for m in messages[-3:]]
    return get_llm().invoke(response_messages).content

# --- NODES ---

def intake_node(state: AgentState):
    """Analyzes conversation and routes flow."""
    print("--- NODE: Intake ---")
    messages = state['messages']
    current_data = state['project_spec']
    
    # 1. Extraction
    extracted = analyze_conversation(messages, current_data)
    if extracted:
        print(f"🔍 Extracted: {extracted}")
        current_data.update(extracted)
        state['project_spec'] = current_data

    # 2. Validation & Decision
    missing_fields = []
    for req in get_requirements():
        key, val = req['id'], current_data.get(req['id'])
        
        if key == 'service_type' and val and not validate_service(val):
            print(f"⚠️ Invalid service '{val}'. Resetting.")
            current_data[key] = None
            valid_services = ", ".join(get_service_details('all').keys())
            missing_fields.append(f"a valid service type (Available: {valid_services})")
            continue
            
        if val is None:
            missing_fields.append(req['description'])

    if not missing_fields:
        return {"next_step": "scoping", "project_spec": current_data}
    
    # 3. Response Generation
    next_missing = missing_fields[0]
    response_prompt = f"""You are 'Groove', a laid-back, professional, and friendly music producer assistant.
    You're chatting with a potential client. Your vibe is cool but efficient.
    
    Current Project Status: {json.dumps(current_data)}
    Missing Info Needed: {next_missing}
    
    Goal: Ask for '{next_missing}' to move the booking forward.
    
    Guidelines:
    - Acknowledge what they just said in a natural, friendly way (e.g. "Got it," "Sounds cool").
    - Be conversational!
    - Don't be a robot. Act like a real person texting.
    - Ask ONLY for the missing info. Don't overwhelm them.
    - Keep it short and punchy.
    """
    response_msgs = [SystemMessage(content=response_prompt)] + [HumanMessage(content=m) for m in messages[-3:]]
    response = get_llm().invoke(response_msgs)
    
    return {"messages": messages + [response.content], "next_step": "intake", "project_spec": current_data}

def scoping_node(state: AgentState):
    """Checks availability."""
    print("--- NODE: Scoping ---")
    spec = state['project_spec']
    service, slot = spec.get('service_type'), spec.get('requested_slot')
    
    if not service or not slot:
        return {"messages": state['messages'] + ["Error: Missing fields for scoping."], "next_step": "END"}
        
    details = get_service_details(service)
    if not details:
        return {"messages": state['messages'] + ["Error: Service not found."], "next_step": "intake"}
    
    result = check_availability(slot, details['duration'])
    
    if result['available']:
        return {"next_step": "finalize"}
    
    # Handle Busy Slot
    # Handle Busy Slot with Error or No Alternatives
    if result.get('error') or not result.get('alternatives'):
        msg = f"My bad, I couldn't check that date/time properly or it's fully booked. Can you double check the format (DD/MM/YYYY HH:MM) or try another time?"
        spec['requested_slot'] = None # Reset to ask again
        return {"messages": state['messages'] + [msg], "next_step": "intake", "project_spec": spec}

    alt_iso = result['alternatives'][0]
    spec.update({'requested_slot': None, 'candidate_slot': alt_iso})
    
    # Make date readable
    dt = datetime.datetime.fromisoformat(alt_iso)
    readable_date = dt.strftime("%A, %d %B at %H:%M")
    
    msg = f"Yo, that slot is booked. I got an opening on {readable_date}. Does that work for you?"
    return {"messages": state['messages'] + [msg], "next_step": "intake", "project_spec": spec}

def finalize_node(state: AgentState):
    """Writes payload and emails."""
    print("--- NODE: Finalize ---")
    spec = state['project_spec']
    spec.pop("candidate_slot", None)
    
    # Summary
    summary = "NEW LEAD:\n" + "\n".join([f"{k}: {v}" for k, v in spec.items() if k != "producer_summary"])
    spec['producer_summary'] = summary
    
    # JSON Storage
    try:
        with open("app/data/leads.json", "r+") as f:
            data = json.load(f)
            data.append(spec)
            f.seek(0)
            json.dump(data, f, indent=2)
    except FileNotFoundError:
        pass # Should handle this better in prod

    # Email
    resend.api_key = os.getenv("RESEND_API_KEY")
    try:
        resend.Emails.send({
            "from": "onboarding@resend.dev",
            "to": "iradyaacoby@gmail.com",
            "subject": f"New Session: {spec.get('client_name', 'Unknown')}",
            "html": f"<pre>{summary}</pre>"
        })
    except Exception as e:
        print(f"Email failed: {e}")

    msg = f"Awesome! I've sent the details to the producer. Catch you in the studio! 🎧"
    return {"messages": state['messages'] + [msg], "next_step": "END"}

# --- GRAPH BUILD ---
workflow = StateGraph(AgentState)

workflow.add_node("intake", intake_node)
workflow.add_node("scoping", scoping_node)
workflow.add_node("finalize", finalize_node)

workflow.set_entry_point("intake")

# Conditional Edges
def router(state: AgentState):
    return state['next_step']

workflow.add_conditional_edges(
    "intake",
    router,
    {
        "intake": "intake", # Loop for more info (Will interrupt via checkpointer)
        "scoping": "scoping"
    }
)

workflow.add_conditional_edges(
    "scoping",
    router,
    {
        "intake": "intake", # Slot rejected, go back
        "finalize": "finalize"
    }
)

workflow.add_edge("finalize", END)

# Add Checkpointer to enable interrupts/stepping
# checkpointer = MemorySaver()
# app = workflow.compile(checkpointer=checkpointer)

# Just export the workflow now
app_workflow = workflow

if __name__ == "__main__":
    print("Agent Compiled with Checkpointer.")
    print("\n--- Mermaid Graph ---")
    try:
        # Compile a temporary app for visualization
        app = workflow.compile()
        
        # Print text
        print(app.get_graph().draw_mermaid())
        
        # Save Image (Updated path for monorepo)
        png_bytes = app.get_graph().draw_mermaid_png()
        graph_path = os.path.join(os.path.dirname(__file__), "..", "..", "docs", "graph.png")
        with open(graph_path, "wb") as f:
            f.write(png_bytes)
        print(f"\n✅ Graph saved to '{graph_path}'")
    except Exception as e:
        print(f"Could not generate graph visualization: {e}")
    print("---------------------")