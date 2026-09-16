import json
import time
from contextlib import contextmanager
from typing import Any

import redis
from sqlalchemy import delete, select, update
from sqlalchemy.exc import IntegrityError

from backend.config import settings
from backend.db import Session
from backend.errors import DomainError
from backend.models import RateBucket
from backend.observability import CACHE


class Cache:
    def __init__(self):
        self.client: Any = (
            redis.Redis.from_url(
                settings().redis_url, socket_connect_timeout=1, socket_timeout=1, decode_responses=True
            )
            if settings().redis_url
            else None
        )

    def get(self, key: str):
        try:
            value = self.client.get(key) if self.client else None
            CACHE.labels("hit" if value else "miss").inc()
            return json.loads(value) if value else None
        except (redis.RedisError, ValueError):
            CACHE.labels("unavailable").inc()
            return None

    def set(self, key: str, value, ttl: int = 120):
        try:
            if self.client:
                self.client.setex(key, ttl, json.dumps(value))
        except redis.RedisError:
            CACHE.labels("unavailable").inc()

    def invalidate(self, *keys: str):
        try:
            if self.client and keys:
                self.client.delete(*keys)
        except redis.RedisError:
            CACHE.labels("unavailable").inc()

    @contextmanager
    def lock(self, key: str):
        # An optimization only: database constraints remain the correctness boundary.
        lock = self.client.lock(key, timeout=30, blocking_timeout=3) if self.client else None
        acquired = False
        try:
            if lock:
                try:
                    acquired = lock.acquire()
                except redis.RedisError:
                    pass
            yield
        finally:
            if acquired and lock is not None:
                try:
                    lock.release()
                except redis.RedisError:
                    pass

    def rate_limit(self, identity: str, limit: int = 90):
        now = time.time()
        key = f"rate:{identity}:{int(now // 60)}"
        try:
            if self.client:
                count = self.client.eval(
                    "local n=redis.call('INCR',KEYS[1]); if n==1 then redis.call('EXPIRE',KEYS[1],120) end; return n",
                    1,
                    key,
                )
                if count > limit:
                    raise DomainError("Too many requests. Try again in a minute.", 429, "rate_limited")
                return
        except redis.RedisError:
            pass
        try:
            with Session.begin() as db:
                db.execute(delete(RateBucket).where(RateBucket.expires_at < now))
                row = db.get(RateBucket, key)
                if not row:
                    db.add(RateBucket(key=key, count=1, expires_at=now + 120))
                else:
                    db.execute(
                        update(RateBucket).where(RateBucket.key == key).values(count=RateBucket.count + 1)
                    )
        except IntegrityError:
            with Session.begin() as db:
                db.execute(update(RateBucket).where(RateBucket.key == key).values(count=RateBucket.count + 1))
        with Session() as db:
            count = db.scalar(select(RateBucket.count).where(RateBucket.key == key)) or 0
            if count > limit:
                raise DomainError("Too many requests. Try again in a minute.", 429, "rate_limited")


cache = Cache()
