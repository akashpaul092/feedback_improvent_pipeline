"""LLM-as-Judge: response quality, helpfulness, factuality."""
from typing import Any
import json

from app.config import settings
from app.evaluators.base import BaseEvaluator


class LLMJudgeEvaluator(BaseEvaluator):
    """Assess response quality, helpfulness, factuality using LLM."""

    def __init__(self):
        self._client = None

    def _get_client(self):
        if self._client is None and settings.openai_api_key:
            from openai import OpenAI
            self._client = OpenAI(api_key=settings.openai_api_key)
        return self._client

    def evaluate(self, conversation: dict) -> dict[str, Any]:
        """Use LLM to score response quality. Falls back to 0.5 (neutral) when unavailable."""
        client = self._get_client()
        turns = conversation.get("turns", [])
        if not client or not turns:
            return {"response_quality": 0.5, "helpfulness": 0.5, "factuality": 0.5}

        # Get last assistant response
        last_assistant = None
        last_user = None
        for t in reversed(turns):
            if t.get("role") == "assistant" and last_assistant is None:
                last_assistant = t
            elif t.get("role") == "user" and last_user is None:
                last_user = t
            if last_assistant and last_user:
                break

        if not last_assistant:
            return {"response_quality": 0.5, "helpfulness": 0.5, "factuality": 0.5}

        user_msg = last_user.get("content", "") if last_user else ""
        assistant_content = last_assistant.get("content", "") or ""
        tool_calls = last_assistant.get("tool_calls", [])

        prompt = f"""Evaluate this AI agent response. User asked: "{user_msg[:500]}"
Agent response: "{assistant_content[:800] if assistant_content else '(tool calls only)'}"
Tool calls: {len(tool_calls)} tool(s) used.

Return JSON only with scores 0-1:
{{"response_quality": <float>, "helpfulness": <float>, "factuality": <float>}}
Be concise. Scores 0.7-0.95 for reasonable responses."""

        try:
            resp = client.chat.completions.create(
                model="gpt-4o-mini",
                messages=[{"role": "user", "content": prompt}],
                temperature=0,
            )
            text = resp.choices[0].message.content.strip()
            # Extract JSON
            if "```" in text:
                text = text.split("```")[1].replace("json", "").strip()
            data = json.loads(text)
            return {
                "response_quality": float(data.get("response_quality", 0.5)),
                "helpfulness": float(data.get("helpfulness", 0.5)),
                "factuality": float(data.get("factuality", 0.5)),
            }
        except Exception:
            return {"response_quality": 0.5, "helpfulness": 0.5, "factuality": 0.5}
