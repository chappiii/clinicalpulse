import json

import redis.asyncio as redis
from fastapi import Request
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from clinicalpulse.core.exceptions import CohortNotFoundError, LabNotFoundError
from clinicalpulse.db.queries import LAB_LOOKUP, LAB_TIMESERIES


async def get_lab_timeseries(
    db: AsyncSession,
    redis_client: redis.Redis,
    cohort_id: str,
    lab_name: str,
    days: int = 30,
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

    lookup = await db.execute(text(LAB_LOOKUP), {"lab_name": lab_name})
    lab_row = lookup.fetchone()
    if lab_row is None:
        raise LabNotFoundError(lab_name)

    result = await db.execute(
        text(LAB_TIMESERIES),
        {"hadm_ids": hadm_ids, "lab_name": lab_name, "days": days},
    )
    rows = result.fetchall()

    timeseries = [
        {
            "day": row.day.strftime("%Y-%m-%d"),
            "median_value": round(float(row.median_value), 2),
            "min_value": round(float(row.min_value), 2),
            "max_value": round(float(row.max_value), 2),
            "sample_count": row.sample_count,
        }
        for row in rows
    ]

    normal_range = None
    if lab_row.ref_range_lower is not None or lab_row.ref_range_upper is not None:
        normal_range = {
            "lower": float(lab_row.ref_range_lower) if lab_row.ref_range_lower else None,
            "upper": float(lab_row.ref_range_upper) if lab_row.ref_range_upper else None,
        }

    unit = rows[0].unit if rows else None

    return {
        "cohort_id": cohort_id,
        "lab_name": lab_row.label,
        "unit": unit,
        "normal_range": normal_range,
        "timeseries": timeseries,
    }
