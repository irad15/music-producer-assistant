# Architecture: Flow Logic Map

## State Machine Overview
**Pattern**: Linear Guardrailed Graph
**Flow**: `Intake` -> `Scoping` -> `Finalize` -> `End`

This architecture enforces a strict sequence. The agent cannot "Finalize" until "Scoping" is done, and cannot "Scope" until "Intake" is complete.

---

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

---

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

---

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
