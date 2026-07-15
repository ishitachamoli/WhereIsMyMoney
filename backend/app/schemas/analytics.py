from pydantic import BaseModel
from datetime import datetime
from typing import Optional, List


class SpendingByCategory(BaseModel):
    """Matches frontend CategoryBreakdown type."""
    category: str
    total_amount: float
    percentage: float
    transaction_count: int
    average_transaction: float


class TimelineEntry(BaseModel):
    """Matches frontend MonthlyTrend type."""
    month: str
    income: float
    expenses: float
    net: float
    transaction_count: int
    savings_rate: float


class IncomeVsExpenseEntry(BaseModel):
    """Matches frontend IncomeVsExpense type (per-month entry)."""
    month: str
    income: float
    expenses: float


class FinancialSummary(BaseModel):
    """Matches frontend FinancialSummary type."""
    total_income: float
    total_expenses: float
    net_savings: float
    savings_rate: float
    top_category: str
    top_category_amount: float
    transaction_count: int
    date_range: dict  # {"start": str, "end": str}


# ─── Category Deep-Dive Schemas ──────────────────────────────────────────────

class DailySpendingEntry(BaseModel):
    date: str
    amount: float

class MonthlySpendingEntry(BaseModel):
    month: str
    amount: float
    change_pct: Optional[float] = None

class TopTransactionEntry(BaseModel):
    date: str
    description: str
    amount: float

class CategorySummary(BaseModel):
    total: float
    avg_monthly: float
    pct_of_total: float
    count: int
    trend: str  # "increasing" | "decreasing" | "stable"

class CategoryAnalyticsResponse(BaseModel):
    category: str
    daily_spending: List[DailySpendingEntry]
    monthly_spending: List[MonthlySpendingEntry]
    top_transactions: List[TopTransactionEntry]
    summary: CategorySummary


# ─── Income Timeline Schemas ────────────────────────────────────────────────

class IncomeSourceEntry(BaseModel):
    name: str
    amount: float


class IncomeTimelineEntry(BaseModel):
    month: str
    amount: float
    change_pct: Optional[float] = None
    sources: List[IncomeSourceEntry]
