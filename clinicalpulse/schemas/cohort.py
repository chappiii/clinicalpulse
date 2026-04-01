from pydantic import BaseModel


class CohortDefineRequest(BaseModel):
    age_min: int | None = None
    age_max: int | None = None
    gender: str | None = None
    admission_type: str | None = None
    icd_codes: list[str] | None = None
    icd_version: int | None = None


class CohortDefineResponse(BaseModel):
    cohort_id: str
    patient_count: int
    admission_count: int
    filters_applied: dict
    expires_in_seconds: int


class TopDiagnosis(BaseModel):
    icd_code: str
    long_title: str
    freq: int


class CohortMetricsResponse(BaseModel):
    cohort_id: str
    total_admissions: int
    avg_los_hours: float
    mortality_rate_pct: float
    readmission_count: int
    top_diagnoses: list[TopDiagnosis]
