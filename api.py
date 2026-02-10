"""
api.py: FastAPI Backend for "Groove" (Refactored)
"""
from contextlib import asynccontextmanager
import os
from typing import List, Optional
from dotenv import load_dotenv

from fastapi import FastAPI, HTTPException, Request
from fastapi.responses import StreamingResponse
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel

from langgraph.checkpoint.postgres.aio import AsyncPostgresSaver
from langgraph.checkpoint.memory import MemorySaver
from psycopg_pool import AsyncConnectionPool
from agent import app_workflow, create_project_spec_model

# Load Env
load_dotenv()
DB_URI = os.getenv("DATABASE_URL")

# --- LIFECYCLE ---
@asynccontextmanager
async def lifespan(app: FastAPI):
    # Setup Checkpointer (Postgres or Memory)
    if DB_URI:
        print("🔌 Connecting to Supabase Postgres...")
        pool = AsyncConnectionPool(conninfo=DB_URI, max_size=20, open=False)
        await pool.open()
        
        # Init Tables (Autocommit required)
        async with pool.connection() as conn:
            await conn.set_autocommit(True)
            await AsyncPostgresSaver(conn).setup()

        app.state.pool = pool
        app.state.memory = None
        print("✅ Postgres Checkpointer Ready.")
    else:
        print("⚠️ WARNING: DATABASE_URL not set. Memory will be ephemeral.")
        app.state.pool = None
        app.state.memory = MemorySaver()
        print("🧠 MemorySaver Checkpointer Ready (Local/Ephemeral).")
    
    yield
    
    if app.state.pool:
        await app.state.pool.close()
        print("🔌 Database connection closed.")

app = FastAPI(title="Groove API", lifespan=lifespan)
app.add_middleware(CORSMiddleware, allow_origins=["*"], allow_methods=["*"], allow_headers=["*"])

# --- MODELS ---
class Message(BaseModel):
    role: str
    content: str

class ChatRequest(BaseModel):
    messages: List[Message]
    session_id: str = "default_session"

# --- HELPERS ---
def get_checkpointer(app_state):
    """Returns the appropriate checkpointer based on environment."""
    if app_state.pool:
        return AsyncPostgresSaver(app_state.pool)
    return app_state.memory

async def get_initial_state(agent_app, config, user_msg):
    """Determines if we are starting new or appending to existing."""
    state = await agent_app.aget_state(config)
    
    if not state.values:
        # New Session: Create empty spec
        spec_model = create_project_spec_model()
        empty_spec = {k: None for k in spec_model.model_fields.keys()}
        return {
            "messages": [user_msg],
            "project_spec": empty_spec, 
            "next_step": "intake"
        }
    
    # Existing Session: Append
    current_msgs = state.values.get("messages", [])
    await agent_app.aupdate_state(config, {"messages": current_msgs + [user_msg]})
    return None # Use current state

# --- ENDPOINTS ---
@app.post("/api/chat")
async def chat_endpoint(req: ChatRequest, fast_req: Request):
    try:
        user_msg = req.messages[-1].content
        print(f"Incoming Request: {user_msg}")
        
        config = {"configurable": {"thread_id": req.session_id}}
        
        # 1. Compile Graph with Checkpointer
        checkpointer = get_checkpointer(fast_req.app.state)
        agent = app_workflow.compile(checkpointer=checkpointer)
        
        # 2. Get Input Payload (New or Append)
        graph_input = await get_initial_state(agent, config, user_msg)
        
        # 3. Stream Response
        async def event_generator():
            async for event in agent.astream(graph_input, config=config, stream_mode="values"):
                if "messages" in event:
                    last_msg = event['messages'][-1]
                    if last_msg != user_msg:
                        yield last_msg
                        break # Stop after one agent response

        return StreamingResponse(event_generator(), media_type="text/plain")

    except Exception as e:
        print(f"Error: {e}")
        raise HTTPException(status_code=500, detail=str(e))

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
