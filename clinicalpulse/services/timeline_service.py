from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from clinicalpulse.core.exceptions import PatientNotFoundError
from clinicalpulse.db.queries import PATIENT_TIMELINE


async def get_patient_timeline(db: AsyncSession, subject_id: int) -> dict:
    result = await db.execute(text(PATIENT_TIMELINE), {"subject_id": subject_id})
    rows = result.fetchall()

    if not rows:
        raise PatientNotFoundError(subject_id)

    admissions = [
        {
            "hadm_id": row.hadm_id,
            "admittime": row.admittime.isoformat(),
            "dischtime": row.dischtime.isoformat() if row.dischtime else None,
            "admission_type": row.admission_type,
            "discharge_location": row.discharge_location,
            "hospital_expire_flag": row.hospital_expire_flag,
            "los_hours": round(float(row.los_hours), 1) if row.los_hours else None,
            "diagnoses": row.diagnoses or [],
        }
        for row in rows
    ]

    return {"subject_id": subject_id, "admissions": admissions}
