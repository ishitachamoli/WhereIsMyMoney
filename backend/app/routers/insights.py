"""Insights endpoints for automated financial analysis."""
from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session
from typing import Optional
from datetime import datetime

from app.core.database import get_db
from app.core.auth import get_current_user
from app.models.user import User
from app.schemas.insights import (
    RecurringTransaction,
    TopMerchantsResponse,
    VelocityResponse,
    OutlierTransaction,
    DayPatternsResponse,
    PaymentMethodsResponse,
    InsightsSummary,
    SubscriptionsResponse,
)
from app.services import insights_service

router = APIRouter(prefix="/insights", tags=["insights"])


@router.get("/recurring", response_model=list[RecurringTransaction])
def recurring_transactions(
    current_user: User = Depends(get_current_user),
    start_date: Optional[datetime] = None,
    end_date: Optional[datetime] = None,
    db: Session = Depends(get_db),
):
    """Detect recurring transactions (subscriptions, EMIs, regular payments)."""
    return insights_service.get_recurring_transactions(
        db, current_user.id, start_date, end_date
    )


@router.get("/top-merchants", response_model=TopMerchantsResponse)
def top_merchants(
    current_user: User = Depends(get_current_user),
    start_date: Optional[datetime] = None,
    end_date: Optional[datetime] = None,
    limit: int = Query(10, ge=1, le=50),
    db: Session = Depends(get_db),
):
    """Get top merchants by frequency and total spend."""
    return insights_service.get_top_merchants(
        db, current_user.id, start_date, end_date, limit
    )


@router.get("/velocity", response_model=VelocityResponse)
def spending_velocity(
    current_user: User = Depends(get_current_user),
    start_date: Optional[datetime] = None,
    end_date: Optional[datetime] = None,
    db: Session = Depends(get_db),
):
    """Analyze cash flow velocity after salary credits."""
    return insights_service.get_spending_velocity(
        db, current_user.id, start_date, end_date
    )


@router.get("/outliers", response_model=list[OutlierTransaction])
def outlier_transactions(
    current_user: User = Depends(get_current_user),
    start_date: Optional[datetime] = None,
    end_date: Optional[datetime] = None,
    threshold: float = Query(2.0, ge=1.5, le=10.0),
    db: Session = Depends(get_db),
):
    """Find large transaction outliers (>threshold times average)."""
    return insights_service.get_outlier_transactions(
        db, current_user.id, start_date, end_date, threshold
    )


@router.get("/patterns", response_model=DayPatternsResponse)
def day_patterns(
    current_user: User = Depends(get_current_user),
    start_date: Optional[datetime] = None,
    end_date: Optional[datetime] = None,
    db: Session = Depends(get_db),
):
    """Get day-of-month spending patterns (days 1-31)."""
    return insights_service.get_day_of_month_patterns(
        db, current_user.id, start_date, end_date
    )


@router.get("/payment-methods", response_model=PaymentMethodsResponse)
def payment_methods(
    current_user: User = Depends(get_current_user),
    start_date: Optional[datetime] = None,
    end_date: Optional[datetime] = None,
    db: Session = Depends(get_db),
):
    """Get payment method breakdown (UPI, NEFT, POS, etc.)."""
    return insights_service.get_payment_method_breakdown(
        db, current_user.id, start_date, end_date
    )


@router.get("/summary", response_model=InsightsSummary)
def insights_summary(
    current_user: User = Depends(get_current_user),
    start_date: Optional[datetime] = None,
    end_date: Optional[datetime] = None,
    db: Session = Depends(get_db),
):
    """Get combined overview of all insights (top 3 from each)."""
    return insights_service.get_insights_summary(
        db, current_user.id, start_date, end_date
    )


@router.get("/subscriptions", response_model=SubscriptionsResponse)
def subscriptions(
    current_user: User = Depends(get_current_user),
    start_date: Optional[datetime] = None,
    end_date: Optional[datetime] = None,
    db: Session = Depends(get_db),
):
    """Detect subscription-like recurring monthly debits with status and cost projections."""
    return insights_service.get_subscriptions(
        db, current_user.id, start_date, end_date
    )
