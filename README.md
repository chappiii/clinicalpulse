# ClinicalPulse

REST API for querying clinical metrics, lab timeseries, and patient timelines from a MIMIC-IV PostgreSQL database.

## Stack

- **Framework:** FastAPI
- **Database:** PostgreSQL (MIMIC-IV) via asyncpg + SQLAlchemy async
- **Cache:** Redis
- **Validation:** Pydantic v2
- **Logging:** structlog (JSON)

## Setup

```bash
# Clone and install
git clone <repo-url>
cd ClinicalPulse
uv sync

# Configure environment
cp .env.example .env
# Edit .env with your database credentials

# Run the server
uv run uvicorn clinicalpulse.main:app --reload --port 8000
```

## Endpoints

| Method | Path | Description |
|--------|------|-------------|
| GET | `/health` | DB + Redis health check |
| POST | `/cohort/define` | Define a patient cohort by filters |
| GET | `/cohort/{id}/metrics` | Aggregate metrics for a cohort |
| GET | `/cohort/{id}/labs/{lab_name}` | Lab timeseries for a cohort |
| GET | `/patient/{subject_id}/timeline` | Full admission timeline for a patient |

## Development

```bash
# Lint
uv run ruff check .

# Format
uv run ruff format .

# Test
uv run pytest
```
