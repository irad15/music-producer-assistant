"""
agent/tools.py: Helper Functions & Tools

- LLM initialization.
- Conversation analysis & response generation.
- Side-effect helpers: disk persistence and email notifications.
"""
import os
import json
from typing import List, Dict, Any

from langchain_openai import ChatOpenAI
from langchain_core.messages import SystemMessage, HumanMessage
import resend

from app.tools.studio_knowledge import get_requirements
from app.agent.state import create_project_spec_model


def get_llm() -> ChatOpenAI:
    """Returns the configured LLM instance."""
    api_key = os.getenv("OPENAI_API_KEY")
    if not api_key:
        print("❌ ERROR: OPENAI_API_KEY is missing")
    return ChatOpenAI(model="gpt-4o-mini", temperature=0, api_key=api_key)


def analyze_conversation(messages: List[str], current_data: Dict[str, Any]) -> Dict[str, Any]:
    """Extracts structured project fields from conversation history via LLM."""
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
    """Generates a conversational Groove reply asking for the next missing field."""
    system_prompt = f"""You are 'Groove', a laid-back, professional, and friendly music producer assistant.
    You're chatting with a potential client. Your vibe is cool but efficient.

    Current Project Status: {json.dumps(current_data)}
    Missing Info Needed: {missing_field}

    Goal: Ask for '{missing_field}' to move the booking forward.

    Guidelines:
    - Acknowledge what they just said in a natural, friendly way (e.g. "Got it," "Sounds cool").
    - Be conversational!
    - Don't be a robot. Act like a real person texting.
    - Ask ONLY for the missing info. Don't overwhelm them.
    - Keep it short and punchy.
    """
    response_messages = [SystemMessage(content=system_prompt)] + [HumanMessage(content=m) for m in messages[-3:]]
    return get_llm().invoke(response_messages).content


def save_lead_to_disk(spec: Dict[str, Any]) -> None:
    """Appends the finalized lead spec to the local leads.json file."""
    try:
        with open("app/data/leads.json", "r+") as f:
            data = json.load(f)
            data.append(spec)
            f.seek(0)
            json.dump(data, f, indent=2)
    except FileNotFoundError:
        pass  # Should handle this better in prod


def send_notification_email(spec: Dict[str, Any], summary: str) -> None:
    """Sends a new-lead notification email to the producer via Resend."""
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
