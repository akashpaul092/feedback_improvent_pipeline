# AI Agent Evaluation Pipeline

Automated evaluation pipeline for AI agents in production. Detects regressions, aligns evals with user feedback, and generates improvement suggestions. Uses human annotations to calibrate evaluators over time (self-healing).

**Documentation:** [docs/](docs/README.md)

## Architecture

```
┌─────────────┐     ┌──────────────┐     ┌─────────────┐
│  Streamlit  │────▶│  FastAPI     │────▶│  PostgreSQL │
│  UI         │     │  API         │     │  (conversations,
└─────────────┘     └──────┬───────┘     │   evaluations)
                           │             └─────────────┘
                           │
                           ▼
                    ┌──────────────┐
                    │  Redis       │
                    │  (ingestion  │
                    │   queue)     │
                    └──────────────┘
```

### Components

- **Data Ingestion**: POST `/conversations/ingest` — stores in PostgreSQL, queues in Redis
- **Evaluation Framework**: 4 evaluators — LLM-as-Judge, Tool Call, Coherence, Heuristics
- **Feedback Integration**: POST `/feedback/annotations/{id}` — human annotations for calibration
- **Self-Healing**: Calibration aligns evaluators with human feedback; detects blind spots
- **Queue Processing**: POST `/queue/process` — process one conversation from Redis

## Setup

### Prerequisites

- **Python 3.11 or 3.12** (not 3.14 — dependencies don't support it yet)
- Docker & Docker Compose (for full stack)
- OpenAI API key (optional, for LLM-as-Judge)

### Local Development

```bash
# Use Python 3.11 or 3.12 (e.g. brew install python@3.12, then:)
python3.12 -m venv venv
# or: pyenv local 3.12.0 && python -m venv venv

source venv/bin/activate  # or `venv\Scripts\activate` on Windows

# Install dependencies
pip install -r requirements.txt

# Copy env
cp .env.example .env
# Edit .env and add OPENAI_API_KEY

# Start PostgreSQL and Redis (Docker)
docker-compose up -d postgres redis

# Run migrations (or: migrations run automatically when API starts)
alembic upgrade head

# Run API
uvicorn app.main:app --reload --port 8000

# In another terminal: Run Streamlit
streamlit run app/ui/streamlit_app.py
```

### Docker (Full Stack)

```bash
cp .env.example .env
# Add OPENAI_API_KEY to .env

docker-compose up -d
```

- API: http://localhost:8000
- Swagger docs: http://localhost:8000/docs
- Streamlit: http://localhost:8501

## Testing

```bash
pip install -r requirements.txt
pip install -e ".[test]"
pytest tests/ -v
```

Tests use SQLite and FakeRedis — no PostgreSQL or Redis required. Covers API endpoints, evaluators, and queue logic (29 tests).

## API Endpoints

| Method | Endpoint | Description |
|--------|----------|-------------|
| POST | `/conversations/ingest` | Ingest a conversation |
| POST | `/evaluations/run/{conversation_id}` | Run evaluation for a conversation |
| GET | `/evaluations` | List evaluations (filter by conversation_id, agent_version) |
| GET | `/evaluations/suggestions` | Get improvement suggestions |
| GET | `/evaluations/calibration` | Get current calibration params |
| POST | `/evaluations/calibrate` | Run calibration (compare with human annotations) |
| POST | `/feedback/annotations/{conversation_id}` | Add human annotations |
| GET | `/queue/status` | Queue pending count |
| POST | `/queue/process` | Process one from queue |

See [docs/api.md](docs/api.md) for full API reference.

## Scaling Strategy

- **10x**: Increase PostgreSQL pool size, add Redis connection pooling, run multiple API replicas
- **100x**: Add Celery workers for queue processing, shard PostgreSQL, use Redis Cluster

## Database Migrations (Alembic)

Tables are created/updated automatically when the API starts. You can also run migrations manually:

```bash
alembic upgrade head          # Apply all migrations
alembic revision --autogenerate -m "add column x"  # Create new migration after model changes
```

## Documentation

| Doc | Description |
|-----|--------------|
| [docs/architecture.md](docs/architecture.md) | System design and data flow |
| [docs/api.md](docs/api.md) | API reference |
| [docs/setup.md](docs/setup.md) | Setup guide |
| [docs/self-healing.md](docs/self-healing.md) | Calibration and human feedback |

## Trade-offs

- **Optimized for**: Prototype speed, modular evaluators, clear API
- **Deferred**: Full async DB (using sync SQLAlchemy)
