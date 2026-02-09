# Deployment Guide

This project is deployed in two parts:
1.  **Backend (Python/FastAPI)**: Hosted on **Render** (as a Web Service).
2.  **Frontend (Next.js)**: Hosted on **Vercel**.

---

## 🚀 Part 1: Deploy Backend to Render

1.  Push your latest code to GitHub.
2.  Go to [dashboard.render.com](https://dashboard.render.com/).
3.  Click **New +** -> **Web Service**.
4.  Connect your GitHub repository `music-producer-assistant`.
5.  **Configure the Service**:
    *   **Name**: `music-backend` (or similar)
    *   **Runtime**: **Docker** (It should detect the Dockerfile automatically)
    *   **Region**: Frankfurt (or closest to you)
6.  **Environment Variables**:
    Scroll down to "Environment Variables" and add:
    *   `OPENAI_API_KEY`: (Your key)
    *   `RESEND_API_KEY`: (Your key)
    *   *(Optional)* `Google Credentials`: You will need to upload your `credentials.json` and `token.json` or use a different auth method for production. For MVP, you can paste the JSON content into a variable like `GOOGLE_CREDENTIALS_JSON` and update `tools/calendar_mcp.py` to read from it.
7.  Click **Create Web Service**.
8.  **Copy the URL**: Once deployed, copy the URL (e.g., `https://music-backend.onrender.com`).

---

## 🌐 Part 2: Deploy Frontend to Vercel

1.  Go to [vercel.com](https://vercel.com).
2.  Click **Add New** -> **Project**.
3.  Import your `music-producer-assistant` repository.
4.  **Framework Preset**: Next.js (should detect automatically).
5.  **Root Directory**: Click "Edit" and select `frontend`.
6.  **Environment Variables**:
    *   `NEXT_PUBLIC_API_URL`: Paste your Render Backend URL (e.g., `https://music-backend.onrender.com/api/chat`).
    *   **Note**: Make sure to append `/api/chat` if your frontend code expects the full path, or just the base URL if it appends the path itself.
        *   *Check `frontend/components/Chat.tsx`: it likely uses a relative path or a configured base.*
        *   *Update*: In `Chat.tsx`, we are fetching from `http://localhost:8000/api/chat`. We need to change this to use `process.env.NEXT_PUBLIC_API_URL`.
7.  Click **Deploy**.

---

## 🔄 Updates

When you push changes to GitHub:
*   **Vercel** will automatically redeploy the frontend.
*   **Render** will automatically redeploy the backend.
