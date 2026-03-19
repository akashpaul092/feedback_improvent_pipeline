"""Self-healing: calibrate evaluators against human annotations, detect blind spots."""
import json
from pathlib import Path
from typing import Any

# Map human labels to numeric scores for comparison
LABEL_TO_SCORE = {
    "correct": 1.0,
    "incorrect": 0.0,
    "good": 0.9,
    "bad": 0.2,
    "poor": 0.2,
    "excellent": 1.0,
    "acceptable": 0.7,
}


def _human_score(annotations: list[dict], annot_type: str) -> float | None:
    """Extract numeric score from human annotations. Uses majority if multiple."""
    vals = []
    for a in annotations or []:
        if a.get("type") != annot_type:
            continue
        label = (a.get("label") or "").lower().strip()
        if label.isdigit():
            vals.append(min(1.0, max(0.0, int(label) / 5.0)))
        elif label in LABEL_TO_SCORE:
            vals.append(LABEL_TO_SCORE[label])
        elif "correct" in label or "good" in label:
            vals.append(0.9)
        elif "incorrect" in label or "bad" in label:
            vals.append(0.2)
    if not vals:
        return None
    return sum(vals) / len(vals)


class CalibrationService:
    """Calibrate evaluators using human feedback. Improves pipeline over time."""

    def __init__(self, storage_path: str | None = None):
        self._path = Path(storage_path or "data/calibration.json")
        self._path.parent.mkdir(parents=True, exist_ok=True)
        self._calibration = self._load()

    def _load(self) -> dict:
        if self._path.exists():
            try:
                return json.loads(self._path.read_text())
            except Exception:
                pass
        return {
            "response_quality": {"slope": 1.0, "intercept": 0.0, "sample_count": 0},
            "tool_accuracy": {"slope": 1.0, "intercept": 0.0, "sample_count": 0},
            "coherence": {"slope": 1.0, "intercept": 0.0, "sample_count": 0},
        }

    def _save(self):
        self._path.write_text(json.dumps(self._calibration, indent=2))

    def get_calibration(self) -> dict:
        """Return current calibration params."""
        return dict(self._calibration)

    def apply(self, score_name: str, raw_score: float) -> float:
        """Apply calibration: calibrated = slope * raw + intercept, clamped to [0,1]."""
        cal = self._calibration.get(score_name, {"slope": 1.0, "intercept": 0.0})
        s, i = cal.get("slope", 1.0), cal.get("intercept", 0.0)
        return min(1.0, max(0.0, s * raw_score + i))

    def run_calibration(
        self, conversations: list[dict], evaluations: list[dict]
    ) -> dict[str, Any]:
        """
        Compare evaluator scores with human annotations. Update calibration when they diverge.
        Returns calibration result and blind spots.
        """
        # Build eval lookup by conversation_id
        eval_by_conv = {e.get("conversation_id"): e for e in evaluations if e.get("conversation_id")}

        pairs: dict[str, list[tuple[float, float]]] = {
            "response_quality": [],
            "tool_accuracy": [],
            "coherence": [],
        }

        blind_spots = []

        for conv in conversations:
            cid = conv.get("conversation_id")
            eval_data = eval_by_conv.get(cid)
            if not eval_data:
                continue

            annotations = (conv.get("feedback") or {}).get("annotations") or []
            if not annotations:
                continue

            scores = eval_data.get("scores") or {}
            tool_eval = eval_data.get("tool_evaluation") or {}

            # Response quality
            human_rq = _human_score(annotations, "response_quality")
            auto_rq = scores.get("response_quality")
            if human_rq is not None and auto_rq is not None:
                pairs["response_quality"].append((auto_rq, human_rq))
                if human_rq < 0.5 and auto_rq > 0.7:
                    blind_spots.append({
                        "conversation_id": cid,
                        "type": "response_quality",
                        "description": "Human rated poor but evaluator scored high",
                        "human_score": human_rq,
                        "evaluator_score": auto_rq,
                    })

            # Tool accuracy
            human_ta = _human_score(annotations, "tool_accuracy")
            auto_ta = scores.get("tool_accuracy")
            if auto_ta is None:
                sel = tool_eval.get("selection_accuracy", 1)
                param = tool_eval.get("parameter_accuracy", 1)
                exec_ok = 1.0 if tool_eval.get("execution_success") else 0.0
                auto_ta = sel * 0.4 + param * 0.3 + exec_ok * 0.3
            if human_ta is not None and auto_ta is not None:
                pairs["tool_accuracy"].append((auto_ta, human_ta))
                if human_ta < 0.5 and auto_ta > 0.7:
                    blind_spots.append({
                        "conversation_id": cid,
                        "type": "tool_accuracy",
                        "description": "Human rated tool use poor but evaluator scored high",
                        "human_score": human_ta,
                        "evaluator_score": auto_ta,
                    })

            # Coherence
            human_co = _human_score(annotations, "coherence")
            auto_co = scores.get("coherence")
            if human_co is not None and auto_co is not None:
                pairs["coherence"].append((auto_co, human_co))
                if human_co < 0.5 and auto_co > 0.7:
                    blind_spots.append({
                        "conversation_id": cid,
                        "type": "coherence",
                        "description": "Human flagged context loss but evaluator scored high",
                        "human_score": human_co,
                        "evaluator_score": auto_co,
                    })

        # Fit simple linear calibration: human = slope * auto + intercept
        for name, data in pairs.items():
            if len(data) < 3:
                continue
            auto_vals = [p[0] for p in data]
            human_vals = [p[1] for p in data]
            mean_auto = sum(auto_vals) / len(auto_vals)
            mean_human = sum(human_vals) / len(human_vals)
            var_auto = sum((x - mean_auto) ** 2 for x in auto_vals) / len(auto_vals)
            if var_auto < 1e-6:
                continue
            cov = sum((a - mean_auto) * (h - mean_human) for a, h in data) / len(data)
            slope = cov / var_auto
            intercept = mean_human - slope * mean_auto
            # Clamp slope to reasonable range
            slope = min(2.0, max(0.2, slope))
            self._calibration[name] = {
                "slope": round(slope, 4),
                "intercept": round(intercept, 4),
                "sample_count": len(data),
            }

        self._save()

        return {
            "calibration": self.get_calibration(),
            "blind_spots": blind_spots[:20],
            "samples_used": {k: len(v) for k, v in pairs.items()},
        }
