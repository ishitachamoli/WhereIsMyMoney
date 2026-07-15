"""Budget schemas for request/response validation."""
from pydantic import BaseModel, Field
from typing import Optional


class BudgetCreate(BaseModel):
    """Schema for creating a budget."""
    category_name: Optional[str] = Field(None, description="Category name; null means total budget")
    amount: float = Field(..., gt=0, description="Budget limit amount")
    period: str = Field("monthly", pattern="^(monthly|weekly|yearly)$")


class BudgetUpdate(BaseModel):
    """Schema for updating a budget."""
    amount: Optional[float] = Field(None, gt=0)
    period: Optional[str] = Field(None, pattern="^(monthly|weekly|yearly)$")
    is_active: Optional[bool] = None


class BudgetResponse(BaseModel):
    """Schema for budget response with computed spending."""
    id: int
    category_name: Optional[str] = None
    amount: float
    period: str
    spent: float
    remaining: float
    percentage_used: float
    is_over_budget: bool
    is_active: bool

    class Config:
        from_attributes = True


class BudgetAlert(BaseModel):
    """Schema for budget alert."""
    budget_id: int
    category_name: Optional[str] = None
    message: str
    severity: str  # "warning", "danger", "over"
    percentage_used: float


class BudgetSummaryResponse(BaseModel):
    """Schema for overall budget summary."""
    total_budget: float
    total_spent: float
    total_remaining: float
    total_percentage_used: float
    days_remaining_in_period: int
    projected_end_of_period_spend: float
    budgets: list[BudgetResponse]
    alerts: list[BudgetAlert]


class BudgetSuggestion(BaseModel):
    """Schema for an AI-suggested budget with rich analytics."""
    category_name: str
    suggested_amount: float
    confidence: float = Field(..., ge=0, le=1, description="Confidence in the suggestion (0-1)")
    rationale: str = Field(..., description="Human-readable explanation of the suggestion")
    methodology: str = Field(
        ...,
        description="Algorithm used: trend_projection | median_with_buffer | fifty_thirty_twenty | consistency_based",
    )
    avg_monthly_spend: float
    trend: str = Field(..., description="Spending trend: increasing | decreasing | stable")
    months_analyzed: int
    # Backwards-compatible fields (always populated by the service)
    average_spending: float
    reasoning: str


class BudgetSuggestionsResponse(BaseModel):
    """Schema for the list of AI suggestions."""
    suggestions: list[BudgetSuggestion]
