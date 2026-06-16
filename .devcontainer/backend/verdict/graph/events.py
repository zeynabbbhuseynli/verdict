import json
import redis.asyncio as aioredis
from verdict.config import REDIS_URL

_redis: aioredis.Redis | None = None


def get_redis() -> aioredis.Redis:
    global _redis
    if _redis is None:
        _redis = aioredis.from_url(REDIS_URL, decode_responses=True)
    return _redis


async def emit(case_id: str, log_entry: dict):
    """Publish a log entry to the Redis channel for this case."""
    r = get_redis()
    await r.publish(f"case:{case_id}:events", json.dumps(log_entry))
