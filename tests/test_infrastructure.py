import os

import pytest

from backend.cache import cache
from backend.db import engine


@pytest.mark.skipif(not os.environ.get("TEST_REDIS_URL"), reason="requires TEST_REDIS_URL")
def test_redis_cache_and_lock():
    cache.set("test:cache-aside", {"price": 100}, 5)
    assert cache.get("test:cache-aside") == {"price": 100}
    with cache.lock("test:lock"):
        cache.invalidate("test:cache-aside")
    assert cache.get("test:cache-aside") is None


@pytest.mark.skipif(not os.environ.get("TEST_DATABASE_URL"), reason="requires isolated TEST_DATABASE_URL")
def test_postgres_dialect():
    assert engine.dialect.name == "postgresql"
