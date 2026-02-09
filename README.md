# 🎵 AI Music Studio Assistant ("Groove")

A conversational AI agent designed to automate client intake, scheduling, and management for music production studios. Built with **LangGraph**, **FastAPI**, and **Next.js**.

![Graph Visualization](graph.png)

## 🚀 Features

-   **Conversational Intake**: "Groove" persona intelligently gathers client details (Name, Service, Date, Attendees).
-   **Real-Time Scheduling**: Integrates with **Google Calendar API** to check availability and propose alternative slots in real-time.
-   **Context Retention**: Remembers conversation history and context (e.g., knows what "it" refers to when accepting a slot).
-   **Smart Validation**: Validates services against studio offerings and handles timezone-aware date parsing.
-   **Automated Confirmations**: Sends email notifications to the studio manager via **Resend** upon successful booking.

## 🛠️ Tech Stack

-   **Architecture**: Client-Server (Rest API)
-   **Frontend**: Next.js 14, TypeScript, Tailwind CSS, Lucide React
-   **Backend**: Python 3.11+, FastAPI, Uvicorn
-   **AI Orchestration**: LangGraph, LangChain, OpenAI GPT-4o-mini
-   **Data Validation**: Pydantic
-   **External APIs**: Google Calendar, Resend

## 📦 Installation

### Prerequisites
-   Python 3.11+
-   Node.js 18+
-   OpenAI API Key
-   Resend API Key
-   Google Cloud Service Account/OAuth Credentials (for Calendar)

### Backend Setup

1.  **Navigate to root** and create a virtual environment:
    ```bash
    python3 -m venv venv
    source venv/bin/activate
    ```
2.  **Install Dependencies**:
    ```bash
    pip install fastapi uvicorn langgraph langchain-openai python-dotenv google-auth google-auth-oauthlib google-auth-httplib2 google-api-python-client resend
    ```
3.  **Environment Variables**:
    Create a `.env` file in the root directory:
    ```env
    OPENAI_API_KEY=your_openai_key
    RESEND_API_KEY=your_resend_key
    ```
4.  **Google Auth**:
    Place your `credentials.json` (OAuth Client ID) in `auth/credentials.json`.
    Run the auth flow once to generate `token.json` (handled by `tools/calendar_mcp.py`).

### Frontend Setup

1.  **Navigate to frontend**:
    ```bash
    cd frontend
    ```
2.  **Install Dependencies**:
    ```bash
    npm install
    ```

## 🏃‍♂️ Running the App

### 1. Start the Backend API
From the root directory:
```bash
python3 api.py
```
*Server runs at `http://localhost:8000`*

### 2. Start the Frontend Client
From the `frontend` directory:
```bash
npm run dev
```
*App runs at `http://localhost:3000`*

## 🧠 Project Structure

-   `agent.py`: Core LangGraph logic (State Machine, Nodes, Edges).
-   `api.py`: FastAPI application serving the agent via REST.
-   `tools/`: Custom tools for Calendar and Studio knowledge.
-   `config/studio_config.json`: Configuration for services, pricing, and rules.
-   `frontend/`: Next.js Web Application.

## 🚧 Future Improvements (Roadmap)

-   **Streaming Responses**: Enable real-time text streaming for a snappier UX (Phase 5).
-   **Voice Interface**: Add speech-to-text for voice bookings.
-   **Payment Integration**: Stripe link generation in the Finalize step.
