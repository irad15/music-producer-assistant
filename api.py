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

from agent import app as agent_app, create_project_spec_model

app = FastAPI(title="Groove API")

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
        
        # Initialize or Update State
        # We need to see if state exists.
        current_state = agent_app.get_state(config).values
        
        if not current_state:
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
            # Continuing Session
            # We must update the state with the new user message
            # For our graph, we update 'messages' list
            agent_app.update_state(config, {"messages": [user_message]})
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
