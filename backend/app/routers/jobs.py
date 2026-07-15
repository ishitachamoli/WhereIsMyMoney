"""Endpoints for tracking background classification jobs."""
import logging
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.core.auth import get_current_user
from app.models.classification_job import ClassificationJob
from app.models.user import User

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/jobs", tags=["jobs"])


class ClassificationJobResponse(BaseModel):
    """Response schema for classification job status."""

    model_config = {"from_attributes": True}

    id: str
    user_id: int
    bank_statement_id: Optional[int] = None
    total_transactions: int
    classified_transactions: int
    status: str
    started_at: Optional[str] = None
    completed_at: Optional[str] = None
    error: Optional[str] = None
    progress_percent: float = 0.0


def _job_to_response(job: ClassificationJob) -> ClassificationJobResponse:
    progress = 0.0
    if job.total_transactions > 0:
        progress = round((job.classified_transactions / job.total_transactions) * 100, 1)
    return ClassificationJobResponse(
        id=job.id,
        user_id=job.user_id,
        bank_statement_id=job.bank_statement_id,
        total_transactions=job.total_transactions,
        classified_transactions=job.classified_transactions,
        status=job.status,
        started_at=job.started_at.isoformat() if job.started_at else None,
        completed_at=job.completed_at.isoformat() if job.completed_at else None,
        error=job.error,
        progress_percent=progress,
    )


@router.get("/classification/{job_id}", response_model=ClassificationJobResponse)
def get_classification_job(
    job_id: str,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Get the status and progress of a classification job."""
    job = (
        db.query(ClassificationJob)
        .filter(
            ClassificationJob.id == job_id,
            ClassificationJob.user_id == current_user.id,
        )
        .first()
    )
    if not job:
        raise HTTPException(status_code=404, detail="Classification job not found")
    return _job_to_response(job)


@router.get("/classification/active", response_model=Optional[ClassificationJobResponse])
def get_active_classification_job(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Get the user's currently active classification job, if any."""
    job = (
        db.query(ClassificationJob)
        .filter(
            ClassificationJob.user_id == current_user.id,
            ClassificationJob.status.in_(["pending", "running"]),
        )
        .order_by(ClassificationJob.started_at.desc())
        .first()
    )
    if not job:
        return None
    return _job_to_response(job)
