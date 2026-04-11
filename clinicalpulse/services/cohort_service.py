import json
import uuid

import redis.asyncio as redis
from fastapi import Request
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from clinicalpulse.core.config import settings
from clinicalpulse.core.exceptions import CohortNotFoundError
from clinicalpulse.db.queries import COHORT_DEFINE, COHORT_METRICS
from clinicalpulse.schemas.cohort import FiltersApplied


async def define_cohort(
    db: AsyncSession,
    redis_client: redis.Redis,
    *,
    request: Request,
    age_min: int | None,
    age_max: int | None,
    gender: str | None,
    admission_type: str | None,
    icd_codes: list[str] | None,
    icd_version: int | None,
) -> dict:
    result = await db.execute(
        text(COHORT_DEFINE),
        {
            "age_min": age_min,
            "age_max": age_max,
            "gender": gender,
            "admission_type": admission_type,
            "icd_codes": icd_codes,
            "icd_version": icd_version,
        },
    )
    rows = result.fetchall()

    hadm_ids = [row.hadm_id for row in rows]
    subject_ids = {row.subject_id for row in rows}

    cohort_id = str(uuid.uuid4())
    request.state.cohort_id = cohort_id
    request.state.cache_hit = False
    await redis_client.set(
        f"cohort:{cohort_id}",
        json.dumps(hadm_ids),
        ex=settings.cohort_ttl_seconds,
    )

    filters_applied = FiltersApplied(
        age_min=age_min,
        age_max=age_max,
        gender=gender,
        admission_type=admission_type,
        icd_codes=icd_codes,
        icd_version=icd_version,
    )

    return {
        "cohort_id": cohort_id,
        "patient_count": len(subject_ids),
        "admission_count": len(hadm_ids),
        "filters_applied": filters_applied,
        "expires_in_seconds": settings.cohort_ttl_seconds,
    }


async def get_cohort_metrics(
    db: AsyncSession,
    redis_client: redis.Redis,
    cohort_id: str,
    *,
    request: Request,
) -> dict:
    request.state.cohort_id = cohort_id
    raw = await redis_client.get(f"cohort:{cohort_id}")
    if raw is None:
        request.state.cache_hit = False
        raise CohortNotFoundError(cohort_id)

    request.state.cache_hit = True
    hadm_ids = json.loads(raw)

    result = await db.execute(text(COHORT_METRICS), {"hadm_ids": hadm_ids})
    row = result.fetchone()

    return {
        "cohort_id": cohort_id,
        "total_admissions": row.total_admissions,
        "avg_los_hours": float(row.avg_los_hours or 0),
        "mortality_rate_pct": float(row.mortality_rate_pct or 0),
        "readmission_count": row.readmit_count or 0,
        "top_diagnoses": row.top_diagnoses or [],
    }
