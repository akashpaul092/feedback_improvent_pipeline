# Self-Healing (Calibration)

The pipeline improves itself over time by aligning evaluator scores with human feedback.

## How It Works

1. **Human annotations** — Reviewers label conversations (tool_accuracy, response_quality, coherence) as correct/incorrect, good/bad.
2. **Calibration** — Compares evaluator scores with human labels, fits linear params (slope, intercept) per metric.
3. **Application** — New evaluation responses use calibrated scores.
4. **Blind spots** — Detects cases where evaluator says "good" but human says "bad".

## Workflow

1. Ingest conversations and run evaluations.
2. Add human annotations via `POST /feedback/annotations/{conversation_id}`.
3. Run `POST /evaluations/calibrate` (manually or on a schedule).
4. Calibration params are saved to `data/calibration.json`.
5. Future evaluations return calibrated scores.

## Annotation Format

```json
[
  {"type": "tool_accuracy", "label": "correct", "annotator_id": "ann_001"},
  {"type": "response_quality", "label": "good", "annotator_id": "ann_001"},
  {"type": "coherence", "label": "incorrect", "annotator_id": "ann_001"}
]
```

**Types:** `tool_accuracy`, `response_quality`, `coherence`  
**Labels:** `correct`, `incorrect`, `good`, `bad`, `poor`, `excellent`, `acceptable`, or 1–5

## Calibration Response

- **calibration** — Current slope/intercept per metric
- **samples_used** — Number of conversations used for each metric (min 3 to update)
- **blind_spots** — Cases where human said bad but evaluator said good

## Storage

Calibration is stored in `data/calibration.json`. No database migration required.
