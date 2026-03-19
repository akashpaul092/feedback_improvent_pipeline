"""Multi-turn coherence: context maintenance, consistency, references."""
import json
from typing import Any

from app.config import settings
from app.evaluators.base import BaseEvaluator


class CoherenceEvaluator(BaseEvaluator):
    """Check context maintenance and consistency across turns using LLM."""

    def __init__(self):
        self._client = None

    def _get_client(self):
        if self._client is None and settings.openai_api_key:
            from openai import OpenAI
            self._client = OpenAI(api_key=settings.openai_api_key)
        return self._client

    def _evaluate_turn_coherence(
        self, prior_turns: list[dict], current_turn: dict, turn_idx: int
    ) -> tuple[float, str | None]:
        """Use LLM to judge if assistant maintains context. Returns (score, issue_desc)."""
        client = self._get_client()
        if not client:
            return 1.0, None

        # Build prior context
        prior_text = []
        for i, t in enumerate(prior_turns):
            role = t.get("role", "")
            content = t.get("content", "") or ""
            if content:
                prior_text.append(f"Turn {i + 1} ({role}): {content[:300]}")
        prior_str = "\n".join(prior_text[-6:])  # Last 6 turns to stay within limits

        curr_content = current_turn.get("content", "") or ""
        tool_calls = current_turn.get("tool_calls", [])
        curr_str = curr_content[:400] if curr_content else f"(tool calls: {[tc.get('tool_name') for tc in tool_calls]})"

        prompt = f"""Conversation so far:
{prior_str}

Current assistant response (Turn {turn_idx}):
{curr_str}

Does the assistant maintain context from earlier turns? Check:
- References prior user info (order IDs, preferences, addresses)
- No contradictions with what was said before
- Stays on topic

Return JSON only: {{"coherent": true/false, "score": 0.0-1.0, "issues": "brief reason if any"}}
Score 1.0 = perfect context, 0.5 = partial, 0.0 = lost/contradicted context."""

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
            score = float(data.get("score", 1.0))
            issues = data.get("issues", "") or ""
            return score, issues if score < 0.8 else None
        except Exception:
            return 1.0, None

    def evaluate(self, conversation: dict) -> dict[str, Any]:
        turns = conversation.get("turns", [])
        scores = []
        issues = []

        # Only evaluate coherence for long conversations (context loss risk)
        if len(turns) < settings.coherence_turn_threshold:
            return {"coherence_score": 1.0, "issues": []}

        client = self._get_client()
        if not client:
            return {"coherence_score": 0.5, "issues": [{"type": "llm_unavailable", "severity": "low", "description": "Coherence check skipped (no API key)"}]}

        # Evaluate each assistant turn after the first few
        for i in range(3, len(turns)):
            turn = turns[i]
            if turn.get("role") != "assistant":
                continue
            prior = turns[:i]
            score, issue_desc = self._evaluate_turn_coherence(prior, turn, i + 1)
            scores.append(score)
            if issue_desc:
                issues.append({
                    "type": "context_loss",
                    "severity": "warning" if score >= 0.5 else "error",
                    "description": f"Turn {i + 1}: {issue_desc}",
                })

        coherence_score = sum(scores) / len(scores) if scores else 1.0
        return {"coherence_score": round(max(0.5, coherence_score), 2), "issues": issues}
