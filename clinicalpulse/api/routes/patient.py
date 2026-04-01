from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from clinicalpulse.api.deps import get_db
from clinicalpulse.schemas.labs import PatientTimelineResponse
from clinicalpulse.services.timeline_service import get_patient_timeline

router = APIRouter()


@router.get("/patient/{subject_id}/timeline", response_model=PatientTimelineResponse)
async def patient_timeline(
    subject_id: int,
    db: AsyncSession = Depends(get_db),
):
    return await get_patient_timeline(db, subject_id)
