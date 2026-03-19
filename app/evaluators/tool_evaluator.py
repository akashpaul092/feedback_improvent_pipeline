"""Tool call evaluation: selection, parameters, hallucination, execution."""
import json
import re
from typing import Any

from app.config import settings
from app.evaluators.base import BaseEvaluator

# Parameter keys to check for hallucination (food delivery / order domain)
PARAM_KEYS_TO_CHECK = (
    "destination", "date", "date_range",
    "order_id", "restaurant_id", "address", "location", "promo_code",
    "item_id", "quantity", "delivery_time",
)

# Static valid locations (cities/areas for delivery)
VALID_LOCATIONS = {
    "mumbai", "delhi", "bangalore", "chennai", "hyderabad", "pune", "kolkata",
    "gurgaon", "noida", "faridabad", "ghaziabad", "jaipur", "lucknow",
    "andheri", "bandra", "koramangala", "indiranagar", "whitefield",
    "sector 18", "connaught place", "karol bagh", "electronic city",
}

# Parameter validation rules: (format_regex, min_val, max_val) or None
PARAM_VALIDATION = {
    "order_id": (r"^[A-Za-z0-9_-]+$", None, None),  # alphanumeric, underscore, hyphen
    "restaurant_id": (r"^[A-Za-z0-9_-]+$", None, None),
    "date": (r"^\d{4}-\d{2}-\d{2}$", None, None),  # YYYY-MM-DD
    "date_range": (r"^\d{4}-\d{2}-\d{2}/\d{4}-\d{2}-\d{2}$", None, None),  # start/end
    "quantity": (None, 1, 20),
    "delivery_time": (r"^\d{1,2}:\d{2}$", None, None),  # HH:MM or H:MM
}


class ToolCallEvaluator(BaseEvaluator):
    """Verify correct tool selection and parameter accuracy."""

    def __init__(self):
        self._client = None

    def _get_client(self):
        if self._client is None and settings.openai_api_key:
            from openai import OpenAI
            self._client = OpenAI(api_key=settings.openai_api_key)
        return self._client

    def _evaluate_selection(self, user_intent: str, tool_name: str) -> float:
        """Use LLM to judge if the correct tool was selected for the user's intent."""
        client = self._get_client()
        if not client:
            return 0.5

        prompt = f"""User said: "{user_intent[:400]}"
Agent called tool: {tool_name}

Was this the correct tool for the user's request? Consider tools like: search_restaurants, place_order, track_order, cancel_order, get_order_details, apply_promo, update_address, search_menu.

Return JSON only: {{"correct": true/false, "score": 0.0-1.0}}
Score 1.0 = perfect match, 0.5 = partial, 0.0 = wrong tool."""

        try:
            resp = client.chat.completions.create(
                model="gpt-4o-mini",
                messages=[{"role": "user", "content": prompt}],
                temperature=0,
            )
            text = resp.choices[0].message.content.strip()
            if "```" in text:
                text = text.split("```")[1].replace("json", "").strip()
            data = json.loads(text)
            return float(data.get("score", 0.5))
        except Exception:
            return 0.5

    def _validate_param(self, key: str, val: Any) -> tuple[bool, str | None]:
        """Validate parameter format, range, or location. Returns (valid, error_msg)."""
        val_str = str(val).strip()
        if not val_str:
            return True, None

        # Location validation
        if key in ("location", "address", "destination"):
            val_lower = val_str.lower()
            # Check if any valid location is in the value (e.g. "Koramangala, Bangalore")
            if not any(loc in val_lower for loc in VALID_LOCATIONS):
                return False, f"location '{val_str}' not in serviceable areas"

        # Format and range validation
        rule = PARAM_VALIDATION.get(key)
        if rule:
            fmt_regex, min_val, max_val = rule
            if fmt_regex and not re.match(fmt_regex, val_str):
                return False, f"'{key}' has invalid format"
            if min_val is not None:
                try:
                    num = int(val_str)
                    if num < min_val or (max_val and num > max_val):
                        return False, f"'{key}' must be between {min_val} and {max_val}"
                except ValueError:
                    return False, f"'{key}' must be a number"

        return True, None

    def evaluate(self, conversation: dict) -> dict[str, Any]:
        selection_scores = []
        param_violations = 0
        execution_success = True
        issues = []

        turns = conversation.get("turns", [])
        context = " ".join(t.get("content", "") or "" for t in turns if t.get("role") == "user")

        for idx, turn in enumerate(turns):
            tool_calls = turn.get("tool_calls", [])
            if not tool_calls:
                continue

            # Get preceding user message for selection check
            prev_user = ""
            for i in range(idx - 1, -1, -1):
                if turns[i].get("role") == "user":
                    prev_user = turns[i].get("content", "") or ""
                    break

            for tc in tool_calls:
                tool_name = tc.get("tool_name", "")

                # Selection accuracy (LLM-based)
                if tool_name and prev_user:
                    sel_score = self._evaluate_selection(prev_user, tool_name)
                    selection_scores.append(sel_score)
                    if sel_score <= 0.5:
                        issues.append({
                            "type": "wrong_tool",
                            "severity": "error",
                            "description": f"Tool '{tool_name}' may not match user intent",
                        })

                # Execution success
                result = tc.get("result", {})
                if isinstance(result, dict) and result.get("status") == "error":
                    execution_success = False
                    issues.append({
                        "type": "tool_execution",
                        "severity": "error",
                        "description": f"Tool {tool_name} failed: {result.get('error', 'unknown')}",
                    })

                # Parameter hallucination + format/range/location validation
                params = tc.get("parameters", {})
                if params:
                    for key, val in params.items():
                        if key not in PARAM_KEYS_TO_CHECK:
                            continue
                        if not val:
                            continue
                        val_str = str(val)

                        # Format, range, location validation
                        valid, err_msg = self._validate_param(key, val)
                        if not valid:
                            issues.append({
                                "type": "parameter_validation",
                                "severity": "error",
                                "description": err_msg or f"Parameter '{key}' failed validation",
                            })
                            param_violations += 1

                        # Hallucination check (only if context available)
                        if context and val_str not in context:
                            issues.append({
                                "type": "parameter_inference",
                                "severity": "low",
                                "description": f"Parameter '{key}' may be inferred (not explicit in context)",
                            })
                            param_violations += 1

        # parameter_accuracy: 1.0 → 0.9 → 0.8 → 0.7... (minus 0.1 per violation, floor 0.5)
        parameter_accuracy = max(0.5, 1.0 - (param_violations * 0.1))

        selection_accuracy = (
            sum(selection_scores) / len(selection_scores)
            if selection_scores else 1.0
        )

        return {
            "selection_accuracy": round(selection_accuracy, 2),
            "parameter_accuracy": parameter_accuracy,
            "execution_success": execution_success,
            "issues": issues,
        }
