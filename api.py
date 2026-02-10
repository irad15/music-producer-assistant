"""
api.py: FastAPI Backend for "Groove"

Purpose:
- Exposes the LangGraph Agent as a REST API.
- Handles POST /api/chat requests from the Frontend.
- Manages thread persistence (using MemorySaver for MVP).

Endpoints:
- POST /api/chat: Interaction endpoint. Receives user message, returns agent stream.
"""

from fastapi import FastAPI, HTTPException
from fastapi.responses import StreamingResponse
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from typing import List, Optional
import json

from contextlib import asynccontextmanager
import os
from psycopg_pool import AsyncConnectionPool
from langgraph.checkpoint.postgres.aio import AsyncPostgresSaver
from agent import app_workflow, create_project_spec_model

# --- LIFECYCLE & DB ---
DB_URI = os.environ.get("DATABASE_URL")

@asynccontextmanager
async def lifespan(app: FastAPI):
    # Startup
    if not DB_URI:
        print("⚠️ WARNING: DATABASE_URL not set. Memory will be ephemeral.")
        pool = None
    else:
        print("🔌 Connecting to Supabase Postgres...")
        # Fix: Don't open automatically in constructor
        pool = AsyncConnectionPool(conninfo=DB_URI, max_size=20, open=False)
        await pool.open()
        
        # Initialize tables
        async with pool.connection() as conn:
            # CREATE INDEX CONCURRENTLY cannot run in a transaction block
            # We must enable autocommit for this setup step
            await conn.set_autocommit(True)
            checkpointer = AsyncPostgresSaver(conn)
            await checkpointer.setup()
        print("✅ Postgres Checkpointer Ready.")
        
    app.state.pool = pool
    yield
    # Shutdown
    if pool:
        await pool.close()
        print("🔌 Database connection closed.")

app = FastAPI(title="Groove API", lifespan=lifespan)

# Configure CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

class Message(BaseModel):
    role: str
    content: str
    id: Optional[str] = None

class ChatRequest(BaseModel):
    messages: List[Message]
    session_id: str = "default_session"

# ... (Helpers)

# --- ENDPOINTS ---

@app.post("/api/chat")
async def chat_endpoint(request: ChatRequest):
    """
    Main chat handler.
    Streams the agent's response back to the client.
    """
    try:
        # Config for thread (Use Frontend Session ID)
        thread_id = request.session_id
        config = {"configurable": {"thread_id": thread_id}}
        
        # Parse input
        user_message = request.messages[-1].content
        print(f"Incoming Request: {user_message}")
        
        # Initialize Checkpointer
        pool = request.app.state.pool
        
        if pool:
            # Persistent Mode (Postgres)
            checkpointer = AsyncPostgresSaver(pool)
            agent_app = app_workflow.compile(checkpointer=checkpointer)
        else:
            # Fallback Mode (Memory)
            from langgraph.checkpoint.memory import MemorySaver
            checkpointer = MemorySaver()
            agent_app = app_workflow.compile(checkpointer=checkpointer)

        # Initialize or Update State
        # We need to see if state exists.
        current_state = await agent_app.aget_state(config)
        current_values = current_state.values
        
        if not current_values:
            # New Session
            ProjectSpec = create_project_spec_model()
            # Instantiate with defaults (all None)
            empty_spec = {k: None for k in ProjectSpec.model_fields.keys()}
            
            initial_state = {
                "messages": [user_message],
                "project_spec": empty_spec, 
                "next_step": "intake"
            }
            # We don't 'invoke', we 'stream' response
            graph_input = initial_state
        else:
            # Continuing Session - MANUAL APPEND strategy
            current_msgs = current_values.get("messages", [])
            new_history = current_msgs + [user_message]
            
            await agent_app.aupdate_state(config, {"messages": new_history})
            graph_input = None # Start from current state

        # Generator for streaming
        async def event_generator():
            # Run the graph
            async for event in agent_app.astream(graph_input, config=config, stream_mode="values"):
                # "event" contains the updated State
                if "messages" in event:
                    # Hack for MVP: simple logic. if the last message is NOT the user message, yield it.
                    last_msg = event['messages'][-1]
                    if last_msg != user_message:
                        yield last_msg
                        # Stop after one response (Human needs to reply)
                        break
                        
        return StreamingResponse(event_generator(), media_type="text/plain")

    except Exception as e:
        print(f"Error: {e}")
        raise HTTPException(status_code=500, detail=str(e))

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
