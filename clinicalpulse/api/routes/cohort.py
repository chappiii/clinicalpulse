import redis.asyncio as redis
from fastapi import APIRouter, Depends, Request
from sqlalchemy.ext.asyncio import AsyncSession

from clinicalpulse.api.deps import get_db, get_redis
from clinicalpulse.schemas.cohort import (
    CohortDefineRequest,
    CohortDefineResponse,
    CohortMetricsResponse,
)
from clinicalpulse.services.cohort_service import define_cohort, get_cohort_metrics

router = APIRouter(prefix="/cohort")


@router.post("/define", response_model=CohortDefineResponse, response_model_exclude_none=True)
async def cohort_define(
    body: CohortDefineRequest,
    request: Request,
    db: AsyncSession = Depends(get_db),
    redis_client: redis.Redis = Depends(get_redis),
):
    return await define_cohort(
        db,
        redis_client,
        request=request,
        age_min=body.age_min,
        age_max=body.age_max,
        gender=body.gender,
        admission_type=body.admission_type,
        icd_codes=body.icd_codes,
        icd_version=body.icd_version,
    )


@router.get("/{cohort_id}/metrics", response_model=CohortMetricsResponse)
async def cohort_metrics(
    cohort_id: str,
    request: Request,
    db: AsyncSession = Depends(get_db),
    redis_client: redis.Redis = Depends(get_redis),
):
    return await get_cohort_metrics(db, redis_client, cohort_id, request=request)
