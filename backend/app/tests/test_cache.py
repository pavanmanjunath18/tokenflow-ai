"""
Cache service unit tests.

Uses fakeredis.FakeRedis to replace the real Redis client, so these tests
run without a live Redis server and remain fully isolated.
"""

import pytest
import fakeredis
from app.services import cache_service


@pytest.fixture(autouse=True)
def fake_redis_client():
    """Swap the global cache client with an in-memory FakeRedis for each test."""
    fake = fakeredis.FakeRedis(decode_responses=True)
    original = cache_service._client
    cache_service._client = fake
    yield fake
    cache_service._client = original


class TestCacheGetSet:
    def test_set_and_get_dict(self):
        cache_service.cache_set("test:dict", {"value": 42, "label": "hello"}, ttl=60)
        result = cache_service.cache_get("test:dict")
        assert result == {"value": 42, "label": "hello"}

    def test_set_and_get_list(self):
        cache_service.cache_set("test:list", [1, 2, 3], ttl=60)
        result = cache_service.cache_get("test:list")
        assert result == [1, 2, 3]

    def test_set_and_get_nested(self):
        payload = {"items": [{"id": 1, "name": "x"}], "count": 1}
        cache_service.cache_set("test:nested", payload, ttl=60)
        assert cache_service.cache_get("test:nested") == payload

    def test_get_missing_key_returns_none(self):
        assert cache_service.cache_get("nonexistent:key") is None

    def test_overwrite_existing_key(self):
        cache_service.cache_set("test:overwrite", {"v": 1})
        cache_service.cache_set("test:overwrite", {"v": 2})
        assert cache_service.cache_get("test:overwrite") == {"v": 2}

    def test_integer_value(self):
        cache_service.cache_set("test:int", 99)
        assert cache_service.cache_get("test:int") == 99

    def test_string_value(self):
        cache_service.cache_set("test:str", "hello world")
        assert cache_service.cache_get("test:str") == "hello world"


class TestCacheDelete:
    def test_delete_existing_key(self):
        cache_service.cache_set("del:key", "data")
        cache_service.cache_delete("del:key")
        assert cache_service.cache_get("del:key") is None

    def test_delete_nonexistent_key_is_noop(self):
        cache_service.cache_delete("del:missing")  # should not raise

    def test_delete_prefix_removes_matching_keys(self):
        cache_service.cache_set("prefix:a", 1)
        cache_service.cache_set("prefix:b", 2)
        cache_service.cache_set("other:c", 3)
        cache_service.cache_delete_prefix("prefix:")
        assert cache_service.cache_get("prefix:a") is None
        assert cache_service.cache_get("prefix:b") is None
        assert cache_service.cache_get("other:c") == 3

    def test_delete_prefix_no_matching_keys_is_noop(self):
        cache_service.cache_delete_prefix("no_match:")  # should not raise

    def test_delete_prefix_empty_prefix_does_not_crash(self):
        cache_service.cache_set("any:key", 1)
        # Not checking for full wipe — just that it doesn't raise
        cache_service.cache_delete_prefix("")


class TestCachePing:
    def test_ping_returns_true_when_connected(self):
        assert cache_service.ping() is True


class TestCacheGracefulDegradation:
    def test_get_does_not_raise_on_broken_client(self):
        """If Redis is unavailable, cache_get returns None without raising."""
        import unittest.mock as mock
        with mock.patch.object(cache_service, "_get_client", side_effect=Exception("Redis down")):
            result = cache_service.cache_get("any:key")
        assert result is None

    def test_set_does_not_raise_on_broken_client(self):
        import unittest.mock as mock
        with mock.patch.object(cache_service, "_get_client", side_effect=Exception("Redis down")):
            cache_service.cache_set("any:key", {"v": 1})  # should not raise

    def test_ping_returns_false_on_broken_client(self):
        import unittest.mock as mock
        with mock.patch.object(cache_service, "_get_client", side_effect=Exception("Redis down")):
            assert cache_service.ping() is False
