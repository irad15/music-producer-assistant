# Project Documentation: "Groove" AI Studio Manager

This document consolidates the project vision, master plan, and architecture flow.

---

# 1. Project Master Plan

## Project Vision
An AI-powered music studio assistant that handles client intake, checks calendar availability, and notifies the producer.

## B.L.A.S.T. Status Checklist

### Phase 1: B - Blueprint (Vision & Logic) ✅
- [x] Defined Data Schemas (`config/studio_config.json`, `data/leads.json`)
- [x] Defined Tech Stack (LangGraph, FastAPI, Next.js)

### Phase 2: L - Link (Connectivity) ✅
- [x] Integrations Verified: OpenAI, Google Calendar, Resend.
- [x] Handshake Scripts created in `tests/`.

### Phase 3: A - Architect (The Build) ✅
- [x] **Backend Logic**: `agent.py` (Intake -> Scoping -> Finalize).
- [x] **API Layer**: `api.py` (FastAPI).
- [x] **Refactoring**: Dynamic `ProjectSpec` from config.
- [x] **Verification**: `tests/verify_agent_logic.py` passes.

### Phase 4: S - Stylize (Refinement & UI) 🚧 IN PROGRESS
- [ ] **LangSmith**: Tracing configured [DONE].
- [ ] **Frontend**: Initialize Next.js app in `frontend/`.
- [ ] **UI Implementation**: Build Chat Interface with Vercel AI SDK.
- [ ] **Connecting**: Hook Frontend to Backend API.

### Phase 5: T - Trigger (Deployment)
- [ ] **End-to-End Test**: Browser -> FastAPI -> Agent.

---

# 2. Project Map & State Tracking

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

---

# 3. Architecture: Flow Logic Map

## State Machine Overview
**Pattern**: Linear Guardrailed Graph
**Flow**: `Intake` -> `Scoping` -> `Finalize` -> `End`

This architecture enforces a strict sequence. The agent cannot "Finalize" until "Scoping" is done, and cannot "Scope" until "Intake" is complete.

## 1. Node: Intake (The Chat)
**Goal**: Converse with the user to gather the `ProjectSpec`.
**Tools**:
- `StudioKnowledge` (Read-only access to `studio_config.json` for services/prices).

**Logic**:
- The agent is a **Router**.
- **Loop**:
    1. Check `ProjectSpec` state.
    2. If missing fields (`client_name`, `service_type`, `attendee_count`, `requested_slot`):
       - Ask the *next* missing question.
       - Use `StudioKnowledge` to validate user answers (e.g. "We don't do mastering").
    3. If all fields are present and valid:
       - Transition to **Scoping**.

**Exit Condition**: State `ProjectSpec` is fully populated.

## 2. Node: Scoping (The Check)
**Goal**: Verify availability and lock in the slot.
**Tools**:
- `GoogleCalendar` (OAuth Client from Phase 2).

**Logic**:
- **Automatic Step** (Not conversational).
- Input: `requested_slot` and `duration` (from Service Config).
- Action:
    1. Check Calendar for conflict in `[requested_slot, requested_slot + duration]`.
    2. **If Available**:
       - Transition to **Finalize**.
    3. **If Busy**:
       - Find the *next 3 available slots* of the same duration.
       - Return control to **Intake** with a system message: "The requested time is taken. Please propose these alternatives to the user: [Slot A, Slot B, Slot C]."
       - Reset `requested_slot` to null.

**Exit Condition**: A valid, available slot is confirmed.

## 3. Node: Finalize (The Output)
**Goal**: Commit the transaction and notify.
**Tools**:
- `FileAppend` (Writes to `leads.json`).
- `ResendEmail` (Sends summary to Producer).

**Logic**:
- **Automatic Step**.
- Action:
    1. Generate `ProducerSummary` object.
    2. Write to `leads.json`.
    3. Send email to producer.
    4. Respond to user: "I have sent the request to the producer. We will confirm shortly."

**Exit Condition**: End of conversation.

---

# 4. Maintenance Procedures

## 🔄 Refreshing Google Calendar Token

Because the app is currently in "Test Mode" with Google, the OAuth token (`auth/token.json`) **expires every 7 days**.

### When to do this:
*   If the app says "Sorry, I can't reach the studio server" or throws `RefreshError`.
*   If `tests/test_calendar.py` fails.

### Local Development (Laptop)
1.  Run the setup script to re-authenticate:
    ```bash
    uv run auth/setup_auth.py
    ```
2.  A browser window will open. Log in to your Google Account.
3.  The script will verify the login and update `auth/token.json`.
4.  Restart your backend (`uv run api.py`).

### Production (Render)
1.  Perform the **Local Development** steps above to get a fresh `auth/token.json` file on your laptop.
2.  Open `auth/token.json` and copy the entire file content.
3.  Go to your **Render Dashboard** -> **Environment**.
4.  Find the `GOOGLE_TOKEN_JSON` variable.
5.  Paste the *new* content of `token.json` into the value field.
6.  Save changes (Render will automatically redeploy).
