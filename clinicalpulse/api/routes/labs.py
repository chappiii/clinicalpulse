import redis.asyncio as redis
from fastapi import APIRouter, Depends, Query, Request
from sqlalchemy.ext.asyncio import AsyncSession

from clinicalpulse.api.deps import get_db, get_redis
from clinicalpulse.schemas.labs import LabTimeseriesResponse
from clinicalpulse.services.labs_service import get_lab_timeseries

router = APIRouter()


@router.get("/cohort/{cohort_id}/labs/{lab_name}", response_model=LabTimeseriesResponse)
async def lab_timeseries(
    cohort_id: str,
    lab_name: str,
    request: Request,
    days: int = Query(default=30, ge=1, le=365),
    db: AsyncSession = Depends(get_db),
    redis_client: redis.Redis = Depends(get_redis),
):
    return await get_lab_timeseries(
        db, redis_client, cohort_id, lab_name, days, request=request
    )
