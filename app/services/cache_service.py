import json
import redis as redis_lib

_client: redis_lib.Redis = None


def init_cache(redis_url: str):
    global _client
    _client = redis_lib.from_url(redis_url, decode_responses=True)


def get(key: str):
    """Return cached value (parsed from JSON), or None on miss / Redis unavailable."""
    if _client is None:
        return None
    raw = _client.get(key)
    return json.loads(raw) if raw else None


def set(key: str, value, ttl: int):
    """Store value as JSON with TTL (seconds). No-op if Redis unavailable."""
    if _client is None:
        return
    _client.setex(key, ttl, json.dumps(value, default=str))


def delete(key: str):
    """Delete a single cache key. No-op if Redis unavailable."""
    if _client is None:
        return
    _client.delete(key)
