"""
api.py: FastAPI Backend for "Groove"

Purpose:
- Serves the Chat API to the frontend.
- Manages persistent conversation history via Postgres/Memory.
"""
import os
from contextlib import asynccontextmanager
from typing import List, Optional
from dotenv import load_dotenv

from fastapi import FastAPI, HTTPException, Request
from fastapi.responses import StreamingResponse
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel

from langgraph.checkpoint.postgres.aio import AsyncPostgresSaver
from langgraph.checkpoint.memory import MemorySaver
from psycopg_pool import AsyncConnectionPool
from app.agent import app_workflow, create_project_spec_model

# Load environment variables from .env
load_dotenv()
DB_URI = os.getenv("DATABASE_URL")

# --- MODELS ---

class Message(BaseModel):
    role: str
    content: str

class ChatRequest(BaseModel):
    messages: List[Message]
    session_id: str = "default_session"

# --- APP INITIALIZATION ---

app = FastAPI(title="Groove API")
app.add_middleware(CORSMiddleware, allow_origins=["*"], allow_methods=["*"], allow_headers=["*"])

# --- ENDPOINTS ---

@app.post("/api/chat")
async def chat_endpoint(req: ChatRequest, fast_req: Request):
    """
    Main entry point for user messages.
    Compiles the agent with a checkpointer and handles streaming responses.
    """
    try:
        user_msg = req.messages[-1].content
        print(f"Incoming Request: {user_msg}")
        
        config = {"configurable": {"thread_id": req.session_id}}
        
        # 1. Compile Graph with Checkpointer from app state
        checkpointer = fast_req.app.state.checkpointer
        agent = app_workflow.compile(checkpointer=checkpointer)
        
        # 2. Get Input Payload (Determine if new session or append)
        graph_input = await get_initial_state(agent, config, user_msg)
        
        # 3. Stream Response
        async def event_generator():
            async for event in agent.astream(graph_input, config=config, stream_mode="values"):
                if "messages" in event:
                    last_msg = event['messages'][-1]
                    if last_msg != user_msg:
                        yield last_msg
                        break 

        return StreamingResponse(event_generator(), media_type="text/plain")

    except Exception as e:
        print(f"Error in chat endpoint: {e}")
        raise HTTPException(status_code=500, detail=str(e))

# --- HELPERS & LIFECYCLE ---

@asynccontextmanager
async def lifespan(app: FastAPI):
    """Handles startup (DB connection) and shutdown."""
    if DB_URI:
        print("🔌 Connecting to Postgres database...")
        pool = AsyncConnectionPool(conninfo=DB_URI, max_size=20, open=False)
        await pool.open()
        
        async with pool.connection() as conn:
            await conn.set_autocommit(True)
            await AsyncPostgresSaver(conn).setup()

        app.state.pool = pool
        app.state.checkpointer = AsyncPostgresSaver(pool)
        print("✅ Postgres Checkpointer Ready.")
    else:
        print("⚠️ WARNING: DATABASE_URL not set. Memory will be ephemeral.")
        app.state.pool = None
        app.state.checkpointer = MemorySaver()
        print("🧠 MemorySaver Checkpointer Ready.")
    
    yield
    
    if app.state.pool:
        await app.state.pool.close()
        print("🔌 Database connection closed.")

# Re-assign lifespan to the app
app.router.lifespan_context = lifespan

async def get_initial_state(agent_app, config, user_msg):
    """Determines if we are starting new or appending to existing session state."""
    state = await agent_app.aget_state(config)
    
    if not state.values:
        spec_model = create_project_spec_model()
        empty_spec = {k: None for k in spec_model.model_fields.keys()}
        return {
            "messages": [user_msg],
            "project_spec": empty_spec, 
            "next_step": "intake"
        }
    
    current_msgs = state.values.get("messages", [])
    await agent_app.aupdate_state(config, {"messages": current_msgs + [user_msg]})
    return None

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
