"""Analytics endpoints for spending analysis."""
from fastapi import APIRouter, Depends, Query, Path
from sqlalchemy.orm import Session
from typing import Optional
from datetime import datetime

from app.core.database import get_db
from app.core.auth import get_current_user
from app.models.user import User
from app.schemas.analytics import (
    SpendingByCategory,
    TimelineEntry,
    IncomeVsExpenseEntry,
    FinancialSummary,
    CategoryAnalyticsResponse,
    IncomeTimelineEntry,
)
from app.services import analytics_service

router = APIRouter(prefix="/analytics", tags=["analytics"])


@router.get("/spending-by-category", response_model=list[SpendingByCategory])
def spending_by_category(
    current_user: User = Depends(get_current_user),
    start_date: Optional[datetime] = None,
    end_date: Optional[datetime] = None,
    db: Session = Depends(get_db),
):
    """Get spending breakdown by category."""
    return analytics_service.get_spending_by_category(db, current_user.id, start_date, end_date)


@router.get("/timeline", response_model=list[TimelineEntry])
def timeline(
    current_user: User = Depends(get_current_user),
    granularity: str = Query("monthly", pattern="^(weekly|monthly|daily)$"),
    months: Optional[int] = Query(None, ge=1, le=60),
    start_date: Optional[datetime] = None,
    end_date: Optional[datetime] = None,
    db: Session = Depends(get_db),
):
    """Get income/expense timeline data."""
    return analytics_service.get_timeline(db, current_user.id, granularity, start_date, end_date, months)


@router.get("/income-vs-expenses", response_model=list[IncomeVsExpenseEntry])
def income_vs_expenses(
    current_user: User = Depends(get_current_user),
    months: Optional[int] = Query(None, ge=1, le=60),
    start_date: Optional[datetime] = None,
    end_date: Optional[datetime] = None,
    db: Session = Depends(get_db),
):
    """Get per-month income vs expenses breakdown."""
    return analytics_service.get_income_vs_expenses(db, current_user.id, start_date, end_date, months)


@router.get("/summary", response_model=FinancialSummary)
def analytics_summary(
    current_user: User = Depends(get_current_user),
    start_date: Optional[datetime] = None,
    end_date: Optional[datetime] = None,
    db: Session = Depends(get_db),
):
    """Get financial summary with totals, savings rate, and top category."""
    return analytics_service.get_summary(db, current_user.id, start_date, end_date)


@router.get("/category/{category_name}", response_model=CategoryAnalyticsResponse)
def category_analytics(
    category_name: str = Path(..., description="Category name to analyze"),
    current_user: User = Depends(get_current_user),
    start_date: Optional[datetime] = None,
    end_date: Optional[datetime] = None,
    db: Session = Depends(get_db),
):
    """Get deep-dive analytics for a specific spending category."""
    return analytics_service.get_category_analytics(
        db, current_user.id, category_name, start_date, end_date
    )


@router.get("/income-timeline", response_model=list[IncomeTimelineEntry])
def income_timeline(
    current_user: User = Depends(get_current_user),
    months: Optional[int] = Query(None, ge=1, le=60),
    start_date: Optional[datetime] = None,
    end_date: Optional[datetime] = None,
    db: Session = Depends(get_db),
):
    """Get monthly income with source breakdown."""
    return analytics_service.get_income_timeline(db, current_user.id, start_date, end_date, months)
