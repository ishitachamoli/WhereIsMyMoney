"""Pydantic schemas for financial insights endpoints."""
from pydantic import BaseModel
from typing import Optional


class RecurringTransaction(BaseModel):
    """A detected recurring transaction pattern."""
    merchant: str
    average_amount: float
    frequency: str  # "monthly", "weekly", "quarterly"
    occurrence_count: int
    last_date: str
    next_expected_date: Optional[str] = None
    total_spent: float


class TopMerchant(BaseModel):
    """A merchant ranked by frequency or total spend."""
    merchant: str
    transaction_count: int
    total_amount: float
    average_amount: float
    percentage_of_total: float


class TopMerchantsResponse(BaseModel):
    """Response for top merchants endpoint."""
    by_frequency: list[TopMerchant]
    by_total_spend: list[TopMerchant]


class VelocityEntry(BaseModel):
    """Spending velocity after a salary credit."""
    income_date: str
    income_amount: float
    spent_7_days: float
    velocity_7d_percent: float
    days_to_50_percent: Optional[int] = None
    daily_burn_rate: float
    risk_level: str  # "high", "medium", "low"


class VelocityResponse(BaseModel):
    """Response for spending velocity endpoint."""
    entries: list[VelocityEntry]
    average_days_to_50_percent: Optional[float] = None
    average_velocity_7d: float
    overall_risk_level: str


class OutlierTransaction(BaseModel):
    """A large transaction outlier."""
    transaction_id: int
    date: str
    description: str
    amount: float
    transaction_type: str
    times_above_average: float
    is_recurring: bool
    category: Optional[str] = None


class DayPattern(BaseModel):
    """Spending pattern for a specific day of month."""
    day: int
    transaction_count: int
    total_amount: float
    average_amount: float


class DayPatternsResponse(BaseModel):
    """Response for day-of-month patterns endpoint."""
    patterns: list[DayPattern]
    peak_day: int
    peak_amount: float
    lowest_day: int
    lowest_amount: float


class PaymentMethodEntry(BaseModel):
    """Breakdown for a single payment method."""
    method: str
    transaction_count: int
    total_amount: float
    percentage_by_count: float
    percentage_by_amount: float


class PaymentMethodsResponse(BaseModel):
    """Response for payment method breakdown endpoint."""
    methods: list[PaymentMethodEntry]
    digital_percentage: float
    most_used_method: str


class InsightsSummary(BaseModel):
    """Combined summary of top insights."""
    top_recurring: list[RecurringTransaction]
    top_merchants: list[TopMerchant]
    velocity_risk: str
    average_velocity_7d: float
    outlier_count: int
    top_outliers: list[OutlierTransaction]
    peak_spending_day: int
    primary_payment_method: str
    digital_percentage: float


class Subscription(BaseModel):
    """A detected subscription/recurring debit."""
    merchant: str
    monthly_amount: float
    annual_cost: float
    frequency: str
    occurrence_count: int
    last_date: str
    next_expected_date: str
    status: str  # "active" or "possibly_cancelled"


class SubscriptionsResponse(BaseModel):
    """Response for subscription detector endpoint."""
    subscriptions: list[Subscription]
    total_monthly_cost: float
    total_annual_cost: float
    active_count: int
    possibly_cancelled_count: int
    potential_annual_savings: float
