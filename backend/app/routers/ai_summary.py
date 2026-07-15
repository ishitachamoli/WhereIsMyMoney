"""AI-powered financial summary endpoint."""
import logging
from datetime import datetime, timezone

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.core.auth import get_current_user
from app.models.user import User
from app.services.ai_summary_service import (
    generate_summary,
    generate_monthly_summary,
    generate_yearly_recap,
    get_available_months,
)
from app.services import tone_templates

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/ai", tags=["ai"])


@router.get("/summary")
def get_ai_summary(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Generate an AI-powered financial summary for the current user.

    Returns structured JSON with sections:
    - overview: income, expenses, savings rate
    - habits: top merchants, frequency patterns
    - insights: anomalies, trends, recurring payments
    - advice: actionable recommendations

    This is the original/default endpoint, kept for backward compatibility.
    """
    return generate_summary(current_user.id, db)


@router.get("/summary/available-months")
def get_summary_available_months(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Return the months (newest-first) that have transaction data.

    Used by the frontend to populate the month selector. Each entry is shaped
    ``{"month": "2025-03", "label": "March 2025", "transaction_count": 42}``.
    """
    return {"months": get_available_months(db, current_user.id)}


@router.get("/summary/monthly")
def get_monthly_ai_summary(
    month: str = Query(..., description="Target month in YYYY-MM format", pattern=r"^\d{4}-\d{2}$"),
    tone: str = Query("roast", description="One of: roast, praise, executive, fun"),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Generate a tone-flavoured summary for a specific month.

    Args:
        month: Target month in ``YYYY-MM`` format (e.g. ``2025-03``).
        tone: One of ``roast``, ``praise``, ``executive``, ``fun``. Defaults to ``roast``.

    Returns:
        Tone-phrased ``lines`` plus the underlying ``stats`` block. All amounts
        use the user's dominant currency symbol.
    """
    if tone not in tone_templates.VALID_TONES:
        raise HTTPException(
            status_code=400,
            detail=f"Invalid tone '{tone}'. Must be one of {list(tone_templates.VALID_TONES)}.",
        )

    try:
        month_dt = datetime.strptime(month, "%Y-%m")
    except ValueError:
        raise HTTPException(status_code=400, detail="Invalid month format; expected YYYY-MM.")
    if not (1 <= month_dt.month <= 12):
        raise HTTPException(status_code=400, detail="Month component must be between 01 and 12.")

    return generate_monthly_summary(db, current_user.id, month, tone)


@router.get("/summary/yearly")
def get_yearly_ai_recap(
    year: int = Query(..., description="Calendar year, e.g. 2025"),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Generate a Spotify-Wrapped-style recap for a full calendar year.

    Args:
        year: The calendar year (e.g. ``2025``).

    Returns:
        Headline stats, top categories/merchants, surprising stats, achievements,
        a personality title, and a closing narrative. Amounts use the user's
        dominant currency symbol.
    """
    current_year = datetime.now(timezone.utc).year
    if year < 1970 or year > current_year + 1:
        raise HTTPException(
            status_code=400,
            detail=f"Year must be between 1970 and {current_year + 1}.",
        )
    return generate_yearly_recap(db, current_user.id, year)
