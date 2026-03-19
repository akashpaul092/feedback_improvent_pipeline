# Deploy to Render

## Prerequisites

- GitHub (or GitLab/Bitbucket) account
- [Render](https://render.com) account (free tier available, no card required)

## Option 1: Blueprint (One-Click)

1. Push your code to GitHub.
2. Go to [Render Dashboard](https://dashboard.render.com) → **New** → **Blueprint**.
3. Connect your repository and select it.
4. Render will detect `render.yaml` and create:
   - Web Service (API)
   - PostgreSQL database
   - Redis
5. Add **OPENAI_API_KEY** in the service Environment tab (optional).
6. Deploy. Your API will be at `https://try-new-api.onrender.com`.

## Option 2: Manual Setup

### 1. Create Web Service

1. **New** → **Web Service**
2. Connect your GitHub repo
3. Configure:
   - **Name:** try-new-api
   - **Runtime:** Python 3
   - **Build Command:** `pip install -r requirements.txt`
   - **Start Command:** `uvicorn app.main:app --host 0.0.0.0 --port $PORT`

### 2. Add PostgreSQL

1. **New** → **PostgreSQL**
2. Name: try-new-db, Plan: Free
3. After creation, copy the **Internal Database URL**
4. In your Web Service → **Environment** → Add:
   - `DATABASE_URL` = (paste the URL)

### 3. Add Redis

1. **New** → **Redis** (or Key Value)
2. Name: try-new-redis, Plan: Free
3. Copy the connection string
4. In your Web Service → **Environment** → Add:
   - `REDIS_URL` = (paste the URL)

### 4. Optional: OpenAI

- Add `OPENAI_API_KEY` if you want LLM evaluators (otherwise they fall back to 0.5).

## Environment Variables

| Variable | Required | Description |
|----------|----------|-------------|
| DATABASE_URL | Yes | From Render PostgreSQL (auto-set with Blueprint) |
| REDIS_URL | Yes | From Render Redis (auto-set with Blueprint) |
| OPENAI_API_KEY | No | For LLM evaluators |

## URLs

- **API:** `https://try-new-api.onrender.com`
- **Docs:** `https://try-new-api.onrender.com/docs`

## Streamlit

Run Streamlit locally and set `API_URL` to your Render API URL, or deploy Streamlit as a separate Render Web Service with Start Command: `streamlit run app/ui/streamlit_app.py --server.port $PORT --server.address 0.0.0.0`.
