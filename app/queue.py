"""Redis queue for high-throughput conversation ingestion."""
import json
import uuid
from typing import Optional

import redis
from app.config import settings

REDIS_QUEUE_KEY = "eval:pending_conversations"
REDIS_QUEUE_BATCH_KEY = "eval:batch_conversations"


def get_redis() -> redis.Redis:
    """Get Redis connection."""
    return redis.from_url(settings.redis_url, decode_responses=True)


def enqueue_conversation(conversation_data: dict) -> str:
    """Add conversation to Redis queue for processing. Returns job ID."""
    job_id = str(uuid.uuid4())
    payload = {"job_id": job_id, "data": conversation_data}
    r = get_redis()
    r.lpush(REDIS_QUEUE_KEY, json.dumps(payload))
    return job_id


def dequeue_conversation() -> Optional[dict]:
    """Pop a conversation from the queue (blocking). Returns None if empty."""
    r = get_redis()
    result = r.brpop(REDIS_QUEUE_KEY, timeout=1)
    if result:
        _, payload = result
        return json.loads(payload)
    return None


def queue_length() -> int:
    """Get number of pending conversations in queue."""
    r = get_redis()
    return r.llen(REDIS_QUEUE_KEY)
