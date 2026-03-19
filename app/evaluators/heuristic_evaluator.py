"""Heuristic checks: format compliance, latency, required fields."""
from typing import Any

from app.config import settings
from app.evaluators.base import BaseEvaluator


class HeuristicEvaluator(BaseEvaluator):
    """Format compliance, latency thresholds, required fields."""

    def evaluate(self, conversation: dict) -> dict[str, Any]:
        issues = []
        metadata = conversation.get("metadata", {})

        # Check turn structure
        turns = conversation.get("turns", [])

        # Average latency per assistant turn (fair for long conversations)
        total_latency = metadata.get("total_latency_ms")
        assistant_turns = [t for t in turns if t.get("role") == "assistant"]
        if total_latency is not None and assistant_turns:
            avg_latency = total_latency / len(assistant_turns)
            if avg_latency > settings.latency_warning_ms:
                issues.append({
                    "type": "latency",
                    "severity": "warning",
                    "description": f"Avg latency {avg_latency:.0f}ms/turn exceeds {settings.latency_warning_ms}ms target",
                })
        for i, turn in enumerate(turns):
            if turn.get("role") == "assistant":
                if "content" not in turn and "tool_calls" not in turn:
                    issues.append({
                        "type": "format",
                        "severity": "error",
                        "description": f"Turn {i + 1}: Assistant turn missing content and tool_calls",
                    })

        # Per-tool latency
        for turn in turns:
            for tc in turn.get("tool_calls", []):
                latency = tc.get("latency_ms")
                if latency and latency > settings.latency_warning_ms:
                    issues.append({
                        "type": "tool_latency",
                        "severity": "warning",
                        "description": f"Tool {tc.get('tool_name', 'unknown')} took {latency}ms (>{settings.latency_warning_ms}ms)",
                    })

        return {"issues": issues, "passed": len([i for i in issues if i["severity"] == "error"]) == 0}
