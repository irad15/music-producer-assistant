"""
agent.py: The LangGraph Brain aaaa

Purpose:
- Defines the State Machine: Intake -> Scoping -> Finalize.
- Implements the 'Groove' persona and logic router.
- Manages the 'ProjectSpec' state object.
- Uses 'MemorySaver' to allow human-in-the-loop logic (interrupts).
"""
import os
import json
# Load Environment
from dotenv import load_dotenv
load_dotenv(os.path.join(os.path.dirname(__file__), ".env"))
import datetime
from typing import TypedDict, Optional, List
from langgraph.graph import StateGraph, END
from langgraph.checkpoint.memory import MemorySaver
from langchain_openai import ChatOpenAI
from langchain_core.messages import SystemMessage, HumanMessage
from typing import Dict, Any, List, Optional
from pydantic import create_model, Field

# Import Tools
from tools.studio_knowledge import get_service_details, validate_service, get_requirements
from tools.calendar_mcp import check_availability
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
    messages: List[str] # Chat history
    project_spec: Dict[str, Any] # Now a dict, since the model is dynamic
    next_step: str

# --- NODES ---

def intake_node(state: AgentState):
    """
    Conversational Intake Node.
    Analyzes convo to fill ProjectSpec.
    """
    print("--- NODE: Intake ---")
    messages = state['messages']
    current_data = state['project_spec']
    
    # 1. Analyze current state using LLM to extract fields
    api_key = os.getenv("OPENAI_API_KEY")
    if not api_key:
        print("❌ ERROR: OPENAI_API_KEY is missing in agent.py")
    llm = ChatOpenAI(model="gpt-4o-mini", temperature=0, api_key=api_key)
    
    # Re-create model to ensure schema is fresh
    DynamicSpec = create_project_spec_model()
    
    requirements = get_requirements()
    req_desc = "\n".join([f"- {r['id']}: {r['description']}" for r in requirements])
    
    # --- EXTRACTION STEP ---
    # We use a specific prompt to extract data from the CONVERSATION HISTORY
    extraction_system_prompt = f"""
    You are an expert data extractor.
    Your goal is to extract the following fields from the conversation:
    {req_desc}
    
    Existing Data: {json.dumps(current_data)}
    
    Rules:
    - Only extract fields that are EXPLICITLY provided by the user.
    - If a field is already present in Existing Data, do not overwrite it unless the user explicitly updates it.
    - If the user says "My name is Irad", extract client_name="Irad".
    - If the user says "Mixing", extract service_type="mixing" (map to closest valid service).
    - Date Parsing: Prefer DD/MM/YYYY format.
    - Timezone: If user implies local time, extract as Naive ISO string (YYYY-MM-DDTHH:MM:SS) WITHOUT 'Z' or offset.
    - If 'candidate_slot' exists in Existing Data and user says 'ok'/'yes', set 'requested_slot' to that candidate value.
    """
    
    structured_llm = llm.with_structured_output(DynamicSpec)
    # We feed the last few messages to the extractor
    extraction_messages = [SystemMessage(content=extraction_system_prompt)] + [HumanMessage(content=m) for m in messages[-5:]]
    
    try:
        extracted_data = structured_llm.invoke(extraction_messages)
        
        # Merge extracted data into current_data
        # extracted_data is a Pydantic model (ProjectSpec)
        extracted_dict = extracted_data.model_dump(exclude_unset=True, exclude_none=True)
        
        if extracted_dict:
            print(f"🔍 Extracted: {extracted_dict}")
            current_data.update(extracted_dict)
            # Update state with new data
            state['project_spec'] = current_data
    except Exception as e:
        print(f"⚠️ Extraction failed: {e}")

    # --- DECISION STEP ---
    # Now we check what is STILL missing
    missing_fields = []
    
    # --- DECISION STEP ---
    # Now we check what is STILL missing
    missing_fields = []
    
    for req in requirements:
        key = req['id']
        val = current_data.get(key)
        
        # VALIDATION: Check existing values (especially service_type)
        if key == 'service_type' and val:
             if not validate_service(val):
                 print(f"⚠️ Invalid service '{val}' detected. Resetting.")
                 current_data[key] = None
                 val = None # Treat as missing for this loop
                 # Get valid services to show user
                 valid_services = ", ".join(get_service_details('all').keys())
                 missing_fields.append(f"a valid service type (Available: {valid_services})")
                 continue
        
        if val is None:
            missing_fields.append(req['description'])

    if not missing_fields:
        return {"next_step": "scoping", "project_spec": current_data}
    
    # --- RESPONSE GENERATION ---
    # Generate a conversational question for the NEXT missing field
    next_missing = missing_fields[0]
    
    # We provide the UPDATED extracted data so the agent knows what it knows
    response_system_prompt = f"""
    You are 'Groove', a world-class music producer and studio manager. 
    You are cool, professional, and concise. You sound like a human, not a bot.
    
    Your goal is to collect missing information to book a session.
    
    Status:
    - Known Info: {json.dumps(current_data)}
    - Missing Info: {', '.join(missing_fields)}
    
    Task:
    - Acknowledge any new info the user just gave (e.g., "Nice to meet you, Irad!").
    - Ask for the NEXT missing field: "{next_missing}".
    - Ask ONLY ONE question.
    - Keep it short.
    """
    
    # Context for response generation
    response_messages = [SystemMessage(content=response_system_prompt)] + [HumanMessage(content=m) for m in messages[-3:]]
    
    response = llm.invoke(response_messages)
    
    return {"messages": [response.content], "next_step": "intake", "project_spec": current_data}

def scoping_node(state: AgentState):
    """
    Checks availability.
    """
    print("--- NODE: Scoping ---")
    spec = state['project_spec'] # Dict
    
    # We dynamically access fields. We assume 'service_type' and 'requested_slot' exist 
    # because they are in the default config. If user removes them, this node Logic breaks 
    # (which is expected, Layer 1 logic requires certain inputs).
    # Ideally, we'd check if they exist.
    
    service_type = spec.get('service_type')
    requested_slot = spec.get('requested_slot')
    
    if not service_type or not requested_slot:
        # Fallback if config was changed incompatibly
        return {"messages": ["Error: Config missing required fields for Scoping."], "next_step": "END"}
        
    service_details = get_service_details(service_type)
    if not service_details:
         return {"messages": ["Error: Service not found."], "next_step": "intake"}
         
    duration = service_details['duration']
    
    result = check_availability(requested_slot, duration)
    
    if result['available']:
        return {"next_step": "finalize"}
    else:
        # Slot busy
        alternative_iso = result['alternatives'][0]
        msg = f"Yo, that slot is booked. How about {alternative_iso}?"
        # logic to ask user again -> reset slot
        spec['requested_slot'] = None 
        spec['candidate_slot'] = alternative_iso # Store for context
        return {"messages": [msg], "next_step": "intake", "project_spec": spec}

def finalize_node(state: AgentState):
    """
    Writes payload and emails.
    """
    print("--- NODE: Finalize ---")
    spec = state['project_spec'] # Dict
    
    # Cleanup internal fields
    if "candidate_slot" in spec:
        del spec["candidate_slot"]
    
    # 1. Summary
    # Dynamic summary based on what keys we have
    summary_lines = ["NEW LEAD:"]
    for k, v in spec.items():
        if k != "producer_summary":
            summary_lines.append(f"{k}: {v}")
            
    summary = "\n".join(summary_lines)
    spec['producer_summary'] = summary
    
    # 2. Storage
    with open("data/leads.json", "r+") as f:
        data = json.load(f)
        data.append(spec)
        f.seek(0)
        json.dump(data, f, indent=2)
        
    # 3. Email
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

    return {"messages": ["All set! Sent to the producer."], "next_step": "END"}

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
checkpointer = MemorySaver()
app = workflow.compile(checkpointer=checkpointer)

if __name__ == "__main__":
    print("Agent Compiled with Checkpointer.")
    print("\n--- Mermaid Graph ---")
    try:
        # Print text
        print(app.get_graph().draw_mermaid())
        
        # Save Image
        png_bytes = app.get_graph().draw_mermaid_png()
        with open("graph.png", "wb") as f:
            f.write(png_bytes)
        print("\n✅ Graph saved to 'graph.png'")
    except Exception as e:
        print(f"Could not generate graph visualization: {e}")
    print("---------------------")
