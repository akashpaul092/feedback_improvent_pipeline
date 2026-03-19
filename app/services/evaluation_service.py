"""Orchestrates evaluation pipeline and self-updating suggestions."""
import uuid
from typing import Any

from app.evaluators import (
    LLMJudgeEvaluator,
    ToolCallEvaluator,
    CoherenceEvaluator,
    HeuristicEvaluator,
)
from app.config import settings


class EvaluationService:
    """Runs all evaluators and generates improvement suggestions."""

    def __init__(self):
        self.llm_judge = LLMJudgeEvaluator()
        self.tool_eval = ToolCallEvaluator()
        self.coherence = CoherenceEvaluator()
        self.heuristic = HeuristicEvaluator()

    def evaluate(self, conversation: dict) -> dict[str, Any]:
        """Run full evaluation pipeline."""
        evaluation_id = f"eval_{uuid.uuid4().hex[:12]}"

        # Run evaluators
        llm_scores = self.llm_judge.evaluate(conversation)
        tool_result = self.tool_eval.evaluate(conversation)
        coherence_result = self.coherence.evaluate(conversation)
        heuristic_result = self.heuristic.evaluate(conversation)

        # Aggregate scores
        response_quality = llm_scores.get("response_quality", 0.5)
        tool_accuracy = (
            tool_result.get("selection_accuracy", 1) * 0.4
            + tool_result.get("parameter_accuracy", 1) * 0.3
            + (1.0 if tool_result.get("execution_success") else 0) * 0.3
        )
        coherence_score = coherence_result.get("coherence_score", 1.0)

        overall = (response_quality * 0.4 + tool_accuracy * 0.35 + coherence_score * 0.25)

        # Collect issues
        issues = heuristic_result.get("issues", [])
        issues.extend(tool_result.get("issues", []))
        issues.extend(coherence_result.get("issues", []))

        # Generate improvement suggestions (self-updating mechanism)
        suggestions = self._generate_suggestions(conversation, issues, tool_result)

        return {
            "evaluation_id": evaluation_id,
            "conversation_id": conversation.get("conversation_id", ""),
            "scores": {
                "overall": round(overall, 2),
                "response_quality": round(response_quality, 2),
                "tool_accuracy": round(tool_accuracy, 2),
                "coherence": round(coherence_score, 2),
            },
            "tool_evaluation": {
                "selection_accuracy": tool_result.get("selection_accuracy", 1.0),
                "parameter_accuracy": tool_result.get("parameter_accuracy", 1.0),
                "execution_success": tool_result.get("execution_success", True),
            },
            "issues_detected": issues,
            "improvement_suggestions": suggestions,
        }

    def _generate_suggestions(
        self, conversation: dict, issues: list, tool_result: dict
    ) -> list[dict]:
        """Generate improvement suggestions from failure patterns."""
        suggestions = []

        # From heuristic issues
        for issue in issues:
            if issue.get("type") == "latency":
                suggestions.append({
                    "type": "prompt",
                    "suggestion": "Add instruction to prioritize response speed over completeness",
                    "rationale": "Reduce response latency",
                    "confidence": 0.72,
                })
            elif issue.get("type") == "parameter_inference":
                suggestions.append({
                    "type": "prompt",
                    "suggestion": "Add explicit date format instruction (e.g. YYYY-MM-DD)",
                    "rationale": "Reduce date inference errors",
                    "confidence": 0.72,
                })
            elif issue.get("type") == "tool_execution":
                suggestions.append({
                    "type": "tool",
                    "suggestion": "Add parameter validation for tool schema",
                    "rationale": "Prevent tool execution failures",
                    "confidence": 0.8,
                })
            elif issue.get("type") == "wrong_tool":
                suggestions.append({
                    "type": "prompt",
                    "suggestion": "Clarify tool selection logic for user intent (e.g. track vs search vs place order)",
                    "rationale": "Improve tool selection accuracy",
                    "confidence": 0.8,
                })

        # Default suggestion if no issues
        if not suggestions:
            suggestions.append({
                "type": "prompt",
                "suggestion": "Consider adding explicit format instructions for common parameters",
                "rationale": "Proactive improvement",
                "confidence": 0.5,
            })

        return suggestions[:5]  # Limit to 5
