"""Query cache (§10). Keyed by table_version, so an atomic swap (version++) invalidates
the table's cache for free — caching and freshness pull the same lever.

Two backends: Redis in prod, an in-process TTL dict in dev (no Redis required).
"""

from __future__ import annotations

import hashlib
import json
import time
from typing import Any, Protocol


def query_cache_key(table: str, table_version: int, query_payload: dict) -> str:
    blob = json.dumps(query_payload, sort_keys=True, default=str).encode()
    digest = hashlib.sha256(blob).hexdigest()[:24]
    return f"query:{table}:{table_version}:{digest}"


class QueryCache(Protocol):
    def get(self, key: str) -> dict | None: ...
    def set(self, key: str, value: dict, ttl_s: int) -> None: ...


class InMemoryCache:
    def __init__(self) -> None:
        self._store: dict[str, tuple[float, dict]] = {}

    def get(self, key: str) -> dict | None:
        item = self._store.get(key)
        if item is None:
            return None
        expires_at, value = item
        if expires_at < time.time():
            self._store.pop(key, None)
            return None
        return value

    def set(self, key: str, value: dict, ttl_s: int) -> None:
        self._store[key] = (time.time() + ttl_s, value)


class RedisCache:
    def __init__(self, client: Any) -> None:
        self._r = client

    def get(self, key: str) -> dict | None:
        raw = self._r.get(key)
        return json.loads(raw) if raw else None

    def set(self, key: str, value: dict, ttl_s: int) -> None:
        self._r.set(key, json.dumps(value, default=str), ex=ttl_s)
