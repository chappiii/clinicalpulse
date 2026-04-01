import redis.asyncio as redis
from fastapi import APIRouter, Depends
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from clinicalpulse.api.deps import get_db, get_redis
from clinicalpulse.core.state import get_uptime

router = APIRouter()


@router.get("/health")
async def health_check(
    db: AsyncSession = Depends(get_db),
    redis_client: redis.Redis = Depends(get_redis),
):
    db_status = "ok"
    try:
        await db.execute(text("SELECT 1"))
    except Exception:
        db_status = "error"

    redis_status = "ok"
    try:
        await redis_client.ping()
    except Exception:
        redis_status = "error"

    status = "ok" if db_status == "ok" and redis_status == "ok" else "degraded"

    return {
        "status": status,
        "database": db_status,
        "redis": redis_status,
        "uptime_seconds": get_uptime(),
    }
