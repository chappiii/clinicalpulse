# ClinicalPulse

![CI](https://github.com/chappiii/clinicalpulse/actions/workflows/ci.yml/badge.svg)
![Python](https://img.shields.io/badge/python-3.12-blue)
![FastAPI](https://img.shields.io/badge/FastAPI-0.115+-green)


REST API that lets researchers define patient cohorts and query clinical metrics, lab timeseries, and patient timelines from a PostgreSQL database.

The database schema follows the structure of [MIMIC-IV](https://physionet.org/content/mimiciv/3.1/) (Medical Information Mart for Intensive Care), a widely used critical care research database. This project uses **synthetic data** that mirrors the MIMIC-IV schema and table relationships — no real patient data is used or required to run this application.

## Stack

| Layer | Technology |
|-------|------------|
| Framework | FastAPI |
| Database | PostgreSQL via asyncpg + SQLAlchemy (async) |
| Cache | Redis |
| Validation | Pydantic v2 |
| Config | pydantic-settings + `.env` |
| Logging | structlog (JSON output) |
| CI | GitHub Actions (ruff lint + format) |
| Package Manager | uv |

## Prerequisites

- Python 3.12+
- PostgreSQL with a MIMIC-IV compatible schema
- Redis

## Setup

```bash
cp .env.example .env   # configure database and Redis credentials
uv sync                # install dependencies
uv run uvicorn clinicalpulse.main:app --reload --port 8000
```

## Endpoints

| Method | Path | Description |
|--------|------|-------------|
| `GET` | `/health` | DB and Redis health check |
| `POST` | `/cohort/define` | Define a patient cohort by filters (age, gender, ICD codes, etc.) |
| `GET` | `/cohort/{id}/metrics` | Aggregate metrics: LOS, mortality, readmissions, top diagnoses |
| `GET` | `/cohort/{id}/labs/{lab_name}` | Daily median lab values as a timeseries |
| `GET` | `/patient/{subject_id}/timeline` | Full admission history with diagnoses |

## How It Works

1. **Define a cohort** — filter patients by age, gender, admission type, or ICD diagnosis codes. The matching admission IDs are cached in Redis with a TTL.
2. **Query the cohort** — pass the cohort ID to the metrics or labs endpoints. The API pulls the cached IDs from Redis and runs a single optimized SQL query against PostgreSQL.
3. **Browse a patient** — look up any patient's full admission timeline with diagnoses.