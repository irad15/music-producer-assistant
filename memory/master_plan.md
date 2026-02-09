# Master Plan: "Groove" AI Studio Manager

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
