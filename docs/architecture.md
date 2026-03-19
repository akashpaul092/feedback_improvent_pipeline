# Architecture

## Overview

The AI Agent Evaluation Pipeline ingests multi-turn conversations, runs automated evaluators, and uses human feedback to improve over time.

## System Diagram

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

## Components

### Data Ingestion
- **POST /conversations/ingest** — Stores conversations in PostgreSQL and enqueues for evaluation
- Conversations include turns, metadata (latency, mission_completed), and optional feedback

### Evaluation Framework
Four evaluators run on each conversation:

| Evaluator | Purpose |
|-----------|---------|
| **LLM-as-Judge** | Response quality, helpfulness, factuality (OpenAI GPT-4o-mini) |
| **Tool Call** | Selection accuracy, parameter validation, execution success |
| **Coherence** | Multi-turn context maintenance (LLM-based for long conversations) |
| **Heuristics** | Latency thresholds, format compliance, required fields |

### Feedback Integration
- **POST /feedback/annotations/{id}** — Human annotators add labels (tool_accuracy, response_quality, coherence)
- Handles annotator disagreement
- Used for calibration and blind-spot detection

### Self-Healing (Calibration)
- Compares evaluator scores with human annotations
- Updates calibration params (slope, intercept) when they diverge
- Detects blind spots (evaluator says good, human says bad)
- Stored in `data/calibration.json`

### Queue Processing
- **POST /queue/process** — Processes one conversation from Redis
- Async ingestion for high throughput

## Data Flow

1. **Ingest** → Conversation stored in DB, queued in Redis
2. **Process** → Queue worker runs evaluation, stores result
3. **Annotate** → Humans add labels via feedback API
4. **Calibrate** → Periodic calibration job updates evaluator alignment
5. **Display** → API returns calibrated scores to UI
