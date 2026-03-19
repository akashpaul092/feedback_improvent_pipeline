"""Unit tests for Redis queue module."""
import json
from unittest.mock import patch

import pytest
from fakeredis import FakeRedis

from app.queue import (
    enqueue_conversation,
    dequeue_conversation,
    dequeue_conversations,
    queue_length,
    REDIS_QUEUE_KEY,
)


@pytest.fixture
def fake_redis():
    return FakeRedis(decode_responses=True)


def test_enqueue_dequeue_roundtrip(fake_redis):
    """Enqueue and dequeue returns same data."""
    with patch("app.queue.get_redis", return_value=fake_redis):
        payload = {"conversation_id": "c1", "agent_version": "v1", "turns": []}
        enqueue_conversation(payload)
        result = dequeue_conversation()
        assert result is not None
        assert result["data"]["conversation_id"] == "c1"


def test_dequeue_empty_returns_none(fake_redis):
    """Dequeue from empty queue returns None."""
    with patch("app.queue.get_redis", return_value=fake_redis):
        result = dequeue_conversation()
        assert result is None


def test_queue_length(fake_redis):
    """Queue length reflects enqueued items."""
    with patch("app.queue.get_redis", return_value=fake_redis):
        assert queue_length() == 0
        enqueue_conversation({"conversation_id": "c1", "turns": []})
        enqueue_conversation({"conversation_id": "c2", "turns": []})
        assert queue_length() == 2
        dequeue_conversation()
        assert queue_length() == 1


def test_dequeue_conversations_batch(fake_redis):
    """Dequeue multiple returns up to count."""
    with patch("app.queue.get_redis", return_value=fake_redis):
        for i in range(5):
            enqueue_conversation({"conversation_id": f"c{i}", "turns": []})
        results = dequeue_conversations(3)
        assert len(results) == 3
        assert queue_length() == 2
