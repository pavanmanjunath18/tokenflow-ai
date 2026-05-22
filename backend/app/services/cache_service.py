"""
Redis-backed cache service.

All public functions fail silently (log + return None/False) when Redis is
unavailable so the application degrades gracefully without a live Redis server.

Cache key conventions:
  integrations:status              – serialised list[IntegrationStatus], TTL 15 s
  integrations:heartbeat:<source>  – per-connector freshness snapshot, TTL 3600 s
  dashboard:overview:<hash>        – dashboard overview, TTL 60 s
  dashboard:filter-options         – departments + providers, TTL 300 s
"""

import json
import logging
from typing import Any

logger = logging.getLogger(__name__)

_client = None  # lazily initialised; swapped with FakeRedis in tests


def _get_client():
    global _client
    if _client is None:
        import redis as _redis
        from app.config import settings
        _client = _redis.from_url(
            settings.redis_url,
            decode_responses=True,
            socket_connect_timeout=2,
            socket_timeout=2,
        )
    return _client


def cache_get(key: str) -> Any | None:
    try:
        raw = _get_client().get(key)
        return json.loads(raw) if raw else None
    except Exception as exc:
        logger.debug("cache_get(%s) failed: %s", key, exc)
        return None


def cache_set(key: str, value: Any, ttl: int = 60) -> None:
    try:
        _get_client().setex(key, ttl, json.dumps(value, default=str))
    except Exception as exc:
        logger.debug("cache_set(%s) failed: %s", key, exc)


def cache_delete(key: str) -> None:
    try:
        _get_client().delete(key)
    except Exception as exc:
        logger.debug("cache_delete(%s) failed: %s", key, exc)


def cache_delete_prefix(prefix: str) -> None:
    """Delete all keys whose name starts with *prefix*."""
    try:
        client = _get_client()
        keys = client.keys(f"{prefix}*")
        if keys:
            client.delete(*keys)
    except Exception as exc:
        logger.debug("cache_delete_prefix(%s) failed: %s", prefix, exc)


def ping() -> bool:
    try:
        return bool(_get_client().ping())
    except Exception:
        return False


def get_info() -> dict:
    try:
        info = _get_client().info("server")
        return {
            "connected": True,
            "version": info.get("redis_version", "unknown"),
            "uptime_seconds": info.get("uptime_in_seconds", 0),
        }
    except Exception:
        return {"connected": False, "version": "unknown", "uptime_seconds": 0}
