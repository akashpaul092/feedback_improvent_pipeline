"""Unit tests for evaluators."""
import pytest
from app.evaluators.heuristic_evaluator import HeuristicEvaluator
from app.evaluators.tool_evaluator import ToolCallEvaluator
from app.evaluators.coherence_evaluator import CoherenceEvaluator
from app.services.evaluation_service import EvaluationService


class TestHeuristicEvaluator:
    """Heuristic evaluator - no external deps."""

    def test_no_issues_for_good_conversation(self):
        ev = HeuristicEvaluator()
        conv = {
            "turns": [
                {"turn_id": 1, "role": "user", "content": "Hi"},
                {"turn_id": 2, "role": "assistant", "content": "Hello!", "tool_calls": []},
            ],
            "metadata": {"total_latency_ms": 500},
        }
        result = ev.evaluate(conv)
        assert "issues" in result
        assert result["passed"] is True

    def test_flags_high_latency(self):
        ev = HeuristicEvaluator()
        conv = {
            "turns": [
                {"turn_id": 1, "role": "user", "content": "Hi"},
                {"turn_id": 2, "role": "assistant", "content": "Hello", "tool_calls": []},
            ],
            "metadata": {"total_latency_ms": 5000},  # 2500ms per turn > 2000 threshold
        }
        result = ev.evaluate(conv)
        assert len(result["issues"]) >= 1
        assert any(i["type"] == "latency" for i in result["issues"])

    def test_flags_missing_content_and_tool_calls(self):
        ev = HeuristicEvaluator()
        conv = {
            "turns": [
                {"turn_id": 1, "role": "user", "content": "Hi"},
                {"turn_id": 2, "role": "assistant"},  # No content, no tool_calls
            ],
        }
        result = ev.evaluate(conv)
        assert result["passed"] is False
        assert any(i["type"] == "format" for i in result["issues"])


class TestToolCallEvaluator:
    """Tool evaluator - parameter validation without LLM."""

    def test_valid_order_id(self):
        ev = ToolCallEvaluator()
        valid, err = ev._validate_param("order_id", "ORD-123")
        assert valid is True
        assert err is None

    def test_invalid_date_format(self):
        ev = ToolCallEvaluator()
        valid, err = ev._validate_param("date", "01/15/2024")
        assert valid is False
        assert err is not None

    def test_valid_date_format(self):
        ev = ToolCallEvaluator()
        valid, err = ev._validate_param("date", "2024-01-15")
        assert valid is True
        assert err is None

    def test_quantity_out_of_range(self):
        ev = ToolCallEvaluator()
        valid, err = ev._validate_param("quantity", 25)
        assert valid is False
        assert err is not None

    def test_valid_quantity(self):
        ev = ToolCallEvaluator()
        valid, err = ev._validate_param("quantity", 5)
        assert valid is True


class TestCoherenceEvaluator:
    """Coherence evaluator - short conversations skip LLM."""

    def test_short_conversation_returns_default(self):
        ev = CoherenceEvaluator()
        conv = {
            "turns": [
                {"turn_id": 1, "role": "user", "content": "Hi"},
                {"turn_id": 2, "role": "assistant", "content": "Hello"},
            ],
        }
        result = ev.evaluate(conv)
        assert result["coherence_score"] == 1.0
        assert result["issues"] == []


class TestEvaluationService:
    """Evaluation service integration."""

    def test_evaluate_returns_expected_structure(self):
        svc = EvaluationService()
        conv = {
            "conversation_id": "test_conv",
            "agent_version": "v1",
            "turns": [
                {"turn_id": 1, "role": "user", "content": "Track my order ORD123"},
                {"turn_id": 2, "role": "assistant", "content": "Checking...", "tool_calls": []},
            ],
            "metadata": {},
        }
        result = svc.evaluate(conv)
        assert "evaluation_id" in result
        assert result["conversation_id"] == "test_conv"
        assert "scores" in result
        assert "overall" in result["scores"]
        assert "response_quality" in result["scores"]
        assert "tool_accuracy" in result["scores"]
        assert "coherence" in result["scores"]
        assert "tool_evaluation" in result
        assert "issues_detected" in result
        assert "improvement_suggestions" in result
