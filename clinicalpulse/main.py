import time
from contextlib import asynccontextmanager

import structlog
from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse

from clinicalpulse.api.routes import cohort, health, labs, patient
from clinicalpulse.core.exceptions import (
    CohortNotFoundError,
    LabNotFoundError,
    PatientNotFoundError,
)
from clinicalpulse.core.logging import setup_logging
from clinicalpulse.core.state import set_start_time

logger = structlog.stdlib.get_logger()


@asynccontextmanager
async def lifespan(app: FastAPI):
    setup_logging()
    set_start_time()
    logger.info("app_started")
    yield
    logger.info("app_shutdown")


app = FastAPI(title="ClinicalPulse", version="0.1.0", lifespan=lifespan)


@app.exception_handler(CohortNotFoundError)
async def cohort_not_found_handler(request: Request, exc: CohortNotFoundError):
    return JSONResponse(
        status_code=404,
        content={
            "error": "CohortNotFound",
            "message": str(exc),
            "detail": {"cohort_id": exc.cohort_id},
        },
    )


@app.exception_handler(LabNotFoundError)
async def lab_not_found_handler(request: Request, exc: LabNotFoundError):
    return JSONResponse(
        status_code=404,
        content={
            "error": "LabNotFound",
            "message": str(exc),
            "detail": {"lab_name": exc.lab_name},
        },
    )


@app.exception_handler(PatientNotFoundError)
async def patient_not_found_handler(request: Request, exc: PatientNotFoundError):
    return JSONResponse(
        status_code=404,
        content={
            "error": "PatientNotFound",
            "message": str(exc),
            "detail": {"subject_id": exc.subject_id},
        },
    )


@app.middleware("http")
async def logging_middleware(request: Request, call_next):
    start = time.time()
    request.state.cohort_id = None
    request.state.cache_hit = None

    response = await call_next(request)

    duration_ms = round((time.time() - start) * 1000, 1)
    logger.info(
        "request",
        method=request.method,
        path=request.url.path,
        duration_ms=duration_ms,
        status_code=response.status_code,
        cohort_id=request.state.cohort_id,
        cache_hit=request.state.cache_hit,
    )
    return response


app.include_router(health.router)
app.include_router(cohort.router)
app.include_router(labs.router)
app.include_router(patient.router)
