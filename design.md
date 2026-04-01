# ClinicalPulse API — Claude Code Brief

## What we are building
A REST API that lets researchers define patient cohorts from a MIMIC-IV
PostgreSQL database and query clinical metrics, lab timeseries, and patient
timelines against those cohorts.

---

## Database (already exists — do not recreate)

Host: localhost  
Port: 5432  
Database: mimiciv  
User: postgres  

### Schemas and tables

**mimiciv_hosp**
- patients         — subject_id (PK), gender, anchor_age, anchor_year, anchor_year_group, dod
- admissions       — hadm_id (PK), subject_id (FK), admittime, dischtime, deathtime, admission_type, admission_location, discharge_location, insurance, language, marital_status, race, hospital_expire_flag
- diagnoses_icd    — subject_id, hadm_id (FK), seq_num, icd_code, icd_version
- d_icd_diagnoses  — icd_code (PK), icd_version (PK), long_title
- d_labitems       — itemid (PK), label, fluid, category
- labevents        — labevent_id (PK), subject_id, hadm_id (FK), itemid (FK), charttime, valuenum, valueuom, ref_range_lower, ref_range_upper, flag, priority
- mv_readmissions  — materialized view: hadm_id, subject_id, dischtime, readmit_hadm_id, readmit_admittime, days_to_readmit

**mimiciv_icu**
- icustays         — stay_id (PK), subject_id, hadm_id (FK), first_careunit, last_careunit, intime, outtime, los

### Key relationships
- subject_id ties patients → admissions → labevents → diagnoses_icd
- hadm_id ties admissions → diagnoses_icd → labevents → icustays
- itemid ties labevents → d_labitems (get lab name from label column)
- icd_code+icd_version ties diagnoses_icd → d_icd_diagnoses (get full name)

---

## Stack

| Layer        | Library                                      |
|--------------|----------------------------------------------|
| Framework    | FastAPI                                      |
| DB driver    | asyncpg + SQLAlchemy (async, core not ORM)   |
| Validation   | Pydantic v2                                  |
| Cache        | Redis via redis-py (async)                   |
| Config       | pydantic-settings reading from .env          |
| Logging      | Python structlog (JSON output)               |
| Testing      | pytest + pytest-asyncio + httpx              |

---

## Project structure

```
clinicalpulse/
├── main.py
├── .env
├── requirements.txt
├── api/
│   ├── __init__.py
│   ├── deps.py            # get_db(), get_redis() dependency injectors
│   └── routes/
│       ├── __init__.py
│       ├── health.py
│       ├── cohort.py
│       └── labs.py
├── services/
│   ├── __init__.py
│   ├── cohort_service.py
│   ├── metrics_service.py
│   └── labs_service.py
├── db/
│   ├── __init__.py
│   ├── session.py         # async engine + session factory
│   └── queries.py         # all raw SQL as module-level constants
├── schemas/
│   ├── __init__.py
│   ├── cohort.py
│   └── labs.py
├── core/
│   ├── __init__.py
│   ├── config.py
│   └── logging.py
└── tests/
    ├── conftest.py
    └── test_cohort.py
```

---

## Environment variables (.env)

```
DATABASE_URL=postgresql+asyncpg://postgres:yourpassword@localhost:5432/mimiciv
REDIS_URL=redis://localhost:6379/0
COHORT_TTL_SECONDS=300
LOG_LEVEL=INFO
```

---

## Endpoints — build in this order

### 1. GET /health
No auth required.  
Returns DB ping, Redis ping, uptime.

Response:
```json
{
  "status": "ok",
  "database": "ok",
  "redis": "ok",
  "uptime_seconds": 42
}
```

---

### 2. POST /cohort/define
Defines a patient cohort by filtering admissions.  
Stores the resulting list of hadm_ids in Redis with a UUID key.

Request body:
```json
{
  "age_min": 18,
  "age_max": 89,
  "gender": "M",
  "admission_type": "EW EMER.",
  "icd_codes": ["I10", "A41.9"],
  "icd_version": 10
}
```
All fields optional — omitting a field means no filter on that dimension.

SQL logic:
```sql
SELECT DISTINCT a.hadm_id
FROM mimiciv_hosp.admissions a
JOIN mimiciv_hosp.patients p ON p.subject_id = a.subject_id
LEFT JOIN mimiciv_hosp.diagnoses_icd d ON d.hadm_id = a.hadm_id
WHERE 1=1
  -- apply each filter only if provided:
  AND (p.anchor_age BETWEEN :age_min AND :age_max)
  AND (p.gender = :gender)
  AND (a.admission_type = :admission_type)
  AND (d.icd_code = ANY(:icd_codes) AND d.icd_version = :icd_version)
```

Redis storage:
- Key: `cohort:{uuid4}`
- Value: JSON list of hadm_ids  e.g. `[20000001, 20000045, 20000123]`
- TTL: 300 seconds (from COHORT_TTL_SECONDS env var)

Response:
```json
{
  "cohort_id": "f47ac10b-58cc-4372-a567-0e02b2c3d479",
  "patient_count": 47,
  "admission_count": 63,
  "filters_applied": {
    "age_min": 18,
    "age_max": 89,
    "gender": "M"
  },
  "expires_in_seconds": 300
}
```

---

### 3. GET /cohort/{cohort_id}/metrics
Fetches the hadm_id list from Redis, then runs a single CTE chain
against PostgreSQL to compute all metrics in one query.

If cohort_id not found in Redis → 404:
```json
{"error": "CohortNotFound", "message": "Cohort expired or does not exist.", "cohort_id": "..."}
```

SQL — use a single CTE, do not make multiple round trips:
```sql
WITH cohort AS (
    SELECT unnest(:hadm_ids::int[]) AS hadm_id
),
admissions AS (
    SELECT
        a.hadm_id,
        a.subject_id,
        EXTRACT(EPOCH FROM (a.dischtime - a.admittime)) / 3600.0 AS los_hours,
        a.hospital_expire_flag,
        a.discharge_location
    FROM mimiciv_hosp.admissions a
    JOIN cohort c ON c.hadm_id = a.hadm_id
),
readmissions AS (
    SELECT COUNT(DISTINCT r.hadm_id) AS readmit_count
    FROM mimiciv_hosp.mv_readmissions r
    JOIN cohort c ON c.hadm_id = r.hadm_id
),
top_dx AS (
    SELECT d.icd_code, di.long_title, COUNT(*) AS freq
    FROM mimiciv_hosp.diagnoses_icd d
    JOIN cohort c ON c.hadm_id = d.hadm_id
    JOIN mimiciv_hosp.d_icd_diagnoses di
        ON di.icd_code = d.icd_code AND di.icd_version = d.icd_version
    WHERE d.seq_num = 1
    GROUP BY d.icd_code, di.long_title
    ORDER BY freq DESC
    LIMIT 5
)
SELECT
    COUNT(*)                                        AS total_admissions,
    ROUND(AVG(los_hours)::numeric, 1)               AS avg_los_hours,
    ROUND(AVG(hospital_expire_flag)::numeric * 100, 1) AS mortality_rate_pct,
    (SELECT readmit_count FROM readmissions)        AS readmit_count,
    (SELECT json_agg(row_to_json(top_dx)) FROM top_dx) AS top_diagnoses
FROM admissions;
```

Response:
```json
{
  "cohort_id": "f47ac10b-...",
  "total_admissions": 63,
  "avg_los_hours": 84.3,
  "mortality_rate_pct": 8.2,
  "readmission_rate_pct": 12.7,
  "top_diagnoses": [
    {"icd_code": "I10", "long_title": "Essential hypertension", "freq": 18},
    {"icd_code": "A41.9", "long_title": "Sepsis, unspecified", "freq": 11}
  ]
}
```

---

### 4. GET /cohort/{cohort_id}/labs/{lab_name}
Returns daily median lab values across the cohort as a timeseries.

Path param `lab_name`: matches `d_labitems.label` case-insensitively
e.g. `Creatinine`, `Hemoglobin`, `White Blood Cells`

Query params:
- `days` (int, default 30) — how many days of data to return

SQL:
```sql
WITH cohort AS (
    SELECT unnest(:hadm_ids::int[]) AS hadm_id
),
item AS (
    SELECT itemid FROM mimiciv_hosp.d_labitems
    WHERE LOWER(label) = LOWER(:lab_name)
    LIMIT 1
)
SELECT
    DATE_TRUNC('day', l.charttime)          AS day,
    PERCENTILE_CONT(0.5) WITHIN GROUP
        (ORDER BY l.valuenum)               AS median_value,
    COUNT(*)                                AS sample_count,
    MIN(l.valuenum)                         AS min_value,
    MAX(l.valuenum)                         AS max_value,
    l.valueuom                              AS unit
FROM mimiciv_hosp.labevents l
JOIN cohort c ON c.hadm_id = l.hadm_id
JOIN item i ON i.itemid = l.itemid
WHERE l.valuenum IS NOT NULL
GROUP BY DATE_TRUNC('day', l.charttime), l.valueuom
ORDER BY day
LIMIT :days;
```

If lab_name not found in d_labitems → 404:
```json
{"error": "LabNotFound", "message": "No lab named 'Creatininex' in d_labitems."}
```

Response:
```json
{
  "cohort_id": "f47ac10b-...",
  "lab_name": "Creatinine",
  "unit": "mg/dL",
  "normal_range": {"lower": 0.7, "upper": 1.3},
  "timeseries": [
    {"day": "2144-09-01", "median_value": 1.1, "min_value": 0.8, "max_value": 2.4, "sample_count": 12},
    {"day": "2144-09-02", "median_value": 1.3, "min_value": 0.9, "max_value": 3.1, "sample_count": 9}
  ]
}
```

---

### 5. GET /patient/{subject_id}/timeline
Returns all admissions for one patient with diagnoses per admission.

SQL:
```sql
SELECT
    a.hadm_id,
    a.admittime,
    a.dischtime,
    a.admission_type,
    a.discharge_location,
    a.hospital_expire_flag,
    EXTRACT(EPOCH FROM (a.dischtime - a.admittime)) / 3600.0 AS los_hours,
    json_agg(
        json_build_object(
            'seq_num',   d.seq_num,
            'icd_code',  d.icd_code,
            'long_title', di.long_title
        ) ORDER BY d.seq_num
    ) AS diagnoses
FROM mimiciv_hosp.admissions a
LEFT JOIN mimiciv_hosp.diagnoses_icd d ON d.hadm_id = a.hadm_id
LEFT JOIN mimiciv_hosp.d_icd_diagnoses di
    ON di.icd_code = d.icd_code AND di.icd_version = d.icd_version
WHERE a.subject_id = :subject_id
GROUP BY a.hadm_id, a.admittime, a.dischtime,
         a.admission_type, a.discharge_location, a.hospital_expire_flag
ORDER BY a.admittime;
```

If subject_id not found → 404:
```json
{"error": "PatientNotFound", "message": "No patient with subject_id 99999."}
```

---

## Design rules Claude Code must follow

### Async
- Every DB call uses `async with session.begin()` — no sync DB calls anywhere
- Redis calls use `await redis.get(...)` / `await redis.set(...)`
- No `time.sleep()` — use `asyncio.sleep()` if needed

### SQL
- All queries live in `db/queries.py` as module-level string constants
- No SQL string building in route handlers or services
- All values passed as named bind parameters — never f-strings into SQL
- Use `text()` from SQLAlchemy core to wrap raw SQL strings

### Cohort pattern
- Route handlers never query the DB directly — they call a service function
- Services retrieve hadm_ids from Redis first, then pass to DB query
- If Redis key missing → raise `CohortNotFoundError` (custom exception)
- Custom exceptions defined in `core/exceptions.py` and mapped to HTTP responses in `main.py` via `@app.exception_handler`

### Error responses
All errors use this exact shape:
```json
{
  "error": "CohortNotFound",
  "message": "Human readable explanation.",
  "detail": {}
}
```

### Logging
Every request logs at INFO level:
```json
{
  "event": "request",
  "method": "GET",
  "path": "/cohort/abc/metrics",
  "cohort_id": "abc",
  "duration_ms": 34,
  "cache_hit": false,
  "status_code": 200
}
```
Use structlog with `structlog.contextvars.bind_contextvars()` in middleware.

### Pagination
Any list endpoint uses `?limit=100&offset=0` query params.
Default limit 100, max limit 500. Never return unbounded results.

---

## Build order

1. `core/config.py` and `.env` — settings first
2. `db/session.py` — async engine
3. `core/exceptions.py` — custom exception classes
4. `main.py` — FastAPI app, exception handlers, middleware stub
5. `api/deps.py` — get_db() and get_redis() dependencies
6. `api/routes/health.py` + test it works end to end
7. `db/queries.py` — all SQL constants
8. `schemas/cohort.py` — Pydantic request/response models
9. `services/cohort_service.py` + `api/routes/cohort.py`
10. Test POST /cohort/define → GET /cohort/{id}/metrics
11. `services/labs_service.py` + `api/routes/labs.py`
12. Test GET /cohort/{id}/labs/Creatinine
13. `tests/` — pytest suite covering all routes

---

## Startup command

```bash
uvicorn main:app --reload --host 0.0.0.0 --port 8000
```

## Expected working test sequence

```bash
# 1. Health check
curl http://localhost:8000/health

# 2. Define a cohort
curl -X POST http://localhost:8000/cohort/define \
  -H "Content-Type: application/json" \
  -d '{"age_min": 50, "age_max": 80, "admission_type": "EW EMER."}'

# 3. Get metrics (use cohort_id from step 2)
curl http://localhost:8000/cohort/{cohort_id}/metrics

# 4. Get lab timeseries
curl http://localhost:8000/cohort/{cohort_id}/labs/Creatinine

# 5. Patient timeline
curl http://localhost:8000/patient/10000000/timeline
```