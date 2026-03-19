# API Reference

Base URL: `http://localhost:8000` (or your deployed URL)

## Conversations

### POST /conversations/ingest

Ingest a conversation for evaluation.

**Request body:**
```json
{
  "conversation_id": "conv_abc123",
  "agent_version": "v1.0.0",
  "turns": [
    {"turn_id": 1, "role": "user", "content": "Track my order ORD123"},
    {"turn_id": 2, "role": "assistant", "content": "...", "tool_calls": [...]}
  ],
  "feedback": {"user_rating": 4},
  "metadata": {"total_latency_ms": 1200, "mission_completed": true}
}
```

**Response:** `{ "conversation_id", "agent_version", "status": "queued" }`

---

## Evaluations

### POST /evaluations/run/{conversation_id}

Run evaluation for a conversation (synchronous).

**Response:** Full evaluation result with scores, issues, improvement suggestions.

### GET /evaluations

List evaluations. Query params: `conversation_id`, `agent_version`, `limit` (default 50).

### GET /evaluations/suggestions

Get aggregated improvement suggestions. Query param: `limit` (default 20).

### GET /evaluations/calibration

Get current evaluator calibration params (self-healing state).

### POST /evaluations/calibrate

Run calibration: compare evaluator scores with human annotations, update calibration, detect blind spots.

**Response:**
```json
{
  "calibration": { "response_quality": {...}, "tool_accuracy": {...}, "coherence": {...} },
  "blind_spots": [...],
  "samples_used": { "response_quality": 12, "tool_accuracy": 8, "coherence": 5 }
}
```

---

## Feedback

### POST /feedback/annotations/{conversation_id}

Add human annotations for calibration.

**Request body (JSON array):**
```json
[
  {"type": "tool_accuracy", "label": "correct", "annotator_id": "ann_001"},
  {"type": "response_quality", "label": "good", "annotator_id": "ann_001"}
]
```

**Annotation types:** `tool_accuracy`, `response_quality`, `coherence`  
**Labels:** `correct`, `incorrect`, `good`, `bad`, `poor`, `excellent`, `acceptable`, or 1–5

**Response:** `{ "conversation_id", "annotations_count", "agreement" }`

---

## Queue

### GET /queue/status

Returns `{ "pending": N }` — count of conversations in queue.

### POST /queue/process

Process one conversation from the queue (runs evaluation, stores result).
