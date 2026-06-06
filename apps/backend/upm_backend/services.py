"""Process-wide service container: Gateway, query cache, job runner, load consumer.

Built once at startup from Settings. Dev mode (no Redis) wires the in-process variants
so the whole stack runs in a single process with zero external brokers.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from upm_dataplane import get_gateway

from upm_backend.cache import InMemoryCache, QueryCache, RedisCache
from upm_backend.config import Settings
from upm_backend.jobrunner import CeleryJobRunner, InlineJobRunner, JobRunner
from upm_backend.loadconsumer import LoadConsumer


@dataclass
class AppServices:
    settings: Settings
    gateway: Any
    cache: QueryCache
    job_runner: JobRunner
    redis: Any | None = None
    consumer: LoadConsumer | None = None


def build_services(settings: Settings) -> AppServices:
    gateway = get_gateway()

    if settings.dev_mode:
        return AppServices(
            settings=settings,
            gateway=gateway,
            cache=InMemoryCache(),
            job_runner=InlineJobRunner(gateway),
        )

    import redis as redislib

    client = redislib.from_url(settings.redis_url, decode_responses=True)
    consumer = LoadConsumer(gateway, client)
    return AppServices(
        settings=settings,
        gateway=gateway,
        cache=RedisCache(client),
        job_runner=CeleryJobRunner(settings.redis_url),
        redis=client,
        consumer=consumer,
    )
