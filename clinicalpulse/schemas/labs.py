from pydantic import BaseModel


class LabTimeseriesPoint(BaseModel):
    day: str
    median_value: float
    min_value: float
    max_value: float
    sample_count: int


class NormalRange(BaseModel):
    lower: float | None
    upper: float | None


class LabTimeseriesResponse(BaseModel):
    cohort_id: str
    lab_name: str
    unit: str | None
    normal_range: NormalRange | None
    timeseries: list[LabTimeseriesPoint]


class TimelineDiagnosis(BaseModel):
    seq_num: int | None
    icd_code: str | None
    long_title: str | None


class TimelineAdmission(BaseModel):
    hadm_id: int
    admittime: str
    dischtime: str | None
    admission_type: str
    discharge_location: str | None
    hospital_expire_flag: int
    los_hours: float | None
    diagnoses: list[TimelineDiagnosis]


class PatientTimelineResponse(BaseModel):
    subject_id: int
    admissions: list[TimelineAdmission]
