from collections.abc import AsyncGenerator

import redis.asyncio as redis
from sqlalchemy.ext.asyncio import AsyncSession

from clinicalpulse.core.config import settings
from clinicalpulse.db.session import async_session_factory

_redis_pool: redis.Redis | None = None


async def get_db() -> AsyncGenerator[AsyncSession]:
    async with async_session_factory() as session:
        yield session


async def get_redis() -> AsyncGenerator[redis.Redis]:
    global _redis_pool
    if _redis_pool is None:
        _redis_pool = redis.from_url(settings.redis_url, decode_responses=True)
    yield _redis_pool
