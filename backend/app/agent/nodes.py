"""
agent/nodes.py: Graph Nodes

Nodes only update state (messages, project_spec).
They do NOT decide the next step — that is edges.py's job.
"""
import datetime
from typing import Dict

from app.tools.studio_knowledge import get_service_details, validate_service, get_requirements
from app.tools.calendar_tool import check_availability
from app.agent.state import AgentState
from app.agent.tools import (
    analyze_conversation,
    generate_response,
    save_lead_to_disk,
    send_notification_email,
)


def intake_node(state: AgentState) -> Dict:
    """Extracts data, validates fields, and asks for the next missing piece."""
    print("--- NODE: Intake ---")
    messages = state['messages']
    current_data = state['project_spec']

    # 1. Extract new information from the conversation
    extracted = analyze_conversation(messages, current_data)
    if extracted:
        print(f"🔍 Extracted: {extracted}")
        current_data.update(extracted)

    # 2. Find missing / invalid fields
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

    # 3. If all fields collected, just update spec (edge will route to scoping)
    if not missing_fields:
        return {"project_spec": current_data}

    # 4. Ask for the next missing field (edge will loop back to intake)
    response = generate_response(messages, current_data, missing_field=missing_fields[0])
    return {"messages": messages + [response], "project_spec": current_data}


def scoping_node(state: AgentState) -> Dict:
    """Checks calendar availability for the requested slot."""
    print("--- NODE: Scoping ---")
    spec = state['project_spec']
    service, slot = spec.get('service_type'), spec.get('requested_slot')

    if not service or not slot:
        # Edge will route to intake to re-collect missing fields
        spec['requested_slot'] = None
        return {"project_spec": spec}

    details = get_service_details(service)
    if not details:
        spec['requested_slot'] = None
        return {"messages": state['messages'] + ["Hmm, I couldn't find that service. Let me know which one you want."], "project_spec": spec}

    result = check_availability(slot, details['duration'])

    # Slot is available — leave requested_slot intact so edge routes to finalize
    if result['available']:
        return {"project_spec": spec}

    # Slot is busy or errored — clear requested_slot so edge routes back to intake
    if result.get('error') or not result.get('alternatives'):
        msg = "My bad, I couldn't check that date/time properly or it's fully booked. Can you double check the format (DD/MM/YYYY HH:MM) or try another time?"
        spec['requested_slot'] = None
        return {"messages": state['messages'] + [msg], "project_spec": spec}

    # Suggest the first available alternative, clear slot so edge routes back to intake
    alt_iso = result['alternatives'][0]
    spec.update({'requested_slot': None, 'candidate_slot': alt_iso})
    readable_date = datetime.datetime.fromisoformat(alt_iso).strftime("%A, %d %B at %H:%M")
    msg = f"Yo, that slot is booked. I got an opening on {readable_date}. Does that work for you?"
    return {"messages": state['messages'] + [msg], "project_spec": spec}


def finalize_node(state: AgentState) -> Dict:
    """Persists the lead and notifies the producer."""
    print("--- NODE: Finalize ---")
    spec = state['project_spec']
    spec.pop("candidate_slot", None)

    summary = "NEW LEAD:\n" + "\n".join([f"{k}: {v}" for k, v in spec.items() if k != "producer_summary"])
    spec['producer_summary'] = summary

    save_lead_to_disk(spec)
    send_notification_email(spec, summary)

    msg = "Awesome! I've sent the details to the producer. Catch you in the studio! 🎧"
    return {"messages": state['messages'] + [msg]}
