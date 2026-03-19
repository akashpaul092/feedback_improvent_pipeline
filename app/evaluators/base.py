"""Base evaluator interface."""
from abc import ABC, abstractmethod
from typing import Any


class BaseEvaluator(ABC):
    """Base class for all evaluators."""

    @abstractmethod
    def evaluate(self, conversation: dict) -> dict[str, Any]:
        """Evaluate a conversation and return scores/issues."""
        pass
