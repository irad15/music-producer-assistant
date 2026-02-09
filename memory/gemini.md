# Project Map & State Tracking: "Groove" AI Studio Manager

## 🧠 Product Goal
Build an AI agent that handles client intake, understands the request, suggests a reasonable time slot, and delivers a clean summary to the producer — replacing messy back-and-forth conversations. **This is decision-making automation at the intake stage, not just appointment booking.**

## 🏗️ Technical Stack
1.  **Brain & Logic**: `gpt-4o-mini` orchestrated by **LangGraph** (State Machine).
2.  **Safety**: **Pydantic** for strict `ProjectSpec` validation.
3.  **Interface**: **Next.js (React)** with **Vercel AI SDK** (Streaming).
4.  **Backend**: **FastAPI** serving the agent.
5.  **Tools**: **MCP** (Model Context Protocol) for Google Calendar.
6.  **Storage**: Local `studio_config.json` (Lite RAG) and `leads.json` (or Google Sheets via MCP).
7.  **Notifications**: **Resend API** for sending email summaries to producer.

## 🧩 Core Components
1.  **Client-Facing Intake Agent**: Conducts natural conversational intake. Asks small, smart set of questions based on `studio_config.json`.
2.  **Basic Studio Knowledge (Lite RAG)**: Structured knowledge (Service list, duration, constraints) loaded into context. No vector DB.
3.  **Availability Check**: Simple tool using Google Calendar. suggest nearest valid alternative if preferred time is taken.
4.  **Producer Summary**: The Critical Output. A clear, structured summary for the producer.
5.  **Notification Layer**: Automatic email via Resend API to `producer@example.com` upon session confirmation.

## Data Schemas

### 1. Studio Config Schema (Input Knowledge)
File: `studio_config.json`
```json
{
  "services": {
    "mixing": { "duration": 4, "base_price": 500 },
    "recording": { "duration": 2, "base_price": 300 }
  },
  "rules": ["No smoking", "50% deposit required"]
}
```

### 2. Project Spec Schema (The Output Goal)
File: `leads.json` (Appended to array)
```json
{
  "client_name": "string",
  "service_type": "string",
  "attendee_count": "int",
  "requested_slot": "string (ISO format)",
  "producer_summary": "string (The generated message)"
}
```

## Behavioral Rules
1.  **Tone**: "Vibe-y" (Casual, cool, music-industry aware) but Professional (Respectful, clear, organized).
    *   *Good*: "Yo, I checked the schedule. We're open on Tuesday."
    *   *Bad*: "Greetings. I have queried the database and found availability."
2.  **No Hallucinations**: NEVER invent prices or services. Always look up `studio_config.json`.
3.  **State Machine Enforcement**:
    *   **Phase 1: Intake**: Get name, contact, and rough idea.
    *   **Phase 2: Scoping**: Match to a Service, check Calendar availability.
    *   **Phase 3: Summary**: Confirm details with user, then generate Payload.
4.  **Availability**: If Calendar is busy, offer nearest alternative slots.

## Architectural Invariants
1.  **Determinism**: The `ProducerSummary` must always match the schema.
2.  **Data Flow**: User Input -> Agent Router -> Tool Execution -> Agent Response.
3.  **Persistence**: Every completed session MUST result in a write to `leads.json`.

## Maintenance Log
*To be populated in Phase 5*
