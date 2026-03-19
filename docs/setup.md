# Setup Guide

## Prerequisites

- **Python 3.11 or 3.12** (not 3.14 — dependencies don't support it yet)
- Docker & Docker Compose (for PostgreSQL and Redis)
- OpenAI API key (optional — LLM evaluators fall back to 0.5 when unavailable)

## Local Development

### 1. Clone and create virtual environment

```bash
git clone <repo-url>
cd try_new

python3.12 -m venv venv
source venv/bin/activate   # Windows: venv\Scripts\activate
```

### 2. Install dependencies

```bash
pip install -r requirements.txt
```

### 3. Environment configuration

```bash
cp .env.example .env
# Edit .env and add OPENAI_API_KEY (optional)
```

### 4. Start PostgreSQL and Redis

```bash
docker-compose up -d postgres redis
```

### 5. Run migrations

```bash
alembic upgrade head
```

Migrations also run automatically when the API starts.

### 6. Start the API

```bash
uvicorn app.main:app --reload --port 8000
```

### 7. Start Streamlit UI (optional)

In another terminal:

```bash
streamlit run app/ui/streamlit_app.py
```

- API: http://localhost:8000
- Swagger: http://localhost:8000/docs
- Streamlit: http://localhost:8501

## Docker (Full Stack)

```bash
cp .env.example .env
# Add OPENAI_API_KEY to .env

docker-compose up -d
```

## Ports

| Service | Default Port |
|---------|--------------|
| API | 8000 |
| Streamlit | 8501 |
| PostgreSQL | 5432 |
| Redis | 6379 |
