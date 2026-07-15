"""Budget endpoints for creating, viewing, and managing budgets."""
from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.core.auth import get_current_user
from app.models.user import User
from app.schemas.budget import (
    BudgetCreate,
    BudgetUpdate,
    BudgetResponse,
    BudgetSummaryResponse,
    BudgetSuggestionsResponse,
)
from app.services import budget_service

router = APIRouter(prefix="/budgets", tags=["budgets"])


@router.post("", response_model=BudgetResponse)
def create_budget(
    data: BudgetCreate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Create a new budget for a category or overall."""
    return budget_service.create_budget(
        db, current_user.id, data.category_name, data.amount, data.period
    )


@router.get("", response_model=list[BudgetResponse])
def list_budgets(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """List all active budgets with current spending."""
    return budget_service.get_budgets(db, current_user.id)


@router.get("/summary", response_model=BudgetSummaryResponse)
def budget_summary(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Get overall budget health summary with alerts."""
    return budget_service.get_budget_summary(db, current_user.id)


@router.get("/suggest", response_model=BudgetSuggestionsResponse)
def suggest_budgets(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """AI-powered budget suggestions based on spending history."""
    return budget_service.suggest_budgets(db, current_user.id)


@router.put("/{budget_id}", response_model=BudgetResponse)
def update_budget(
    budget_id: int,
    data: BudgetUpdate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Update an existing budget."""
    updates = data.model_dump(exclude_unset=True)
    return budget_service.update_budget(db, budget_id, current_user.id, updates)


@router.delete("/{budget_id}", status_code=204)
def delete_budget(
    budget_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Delete a budget."""
    budget_service.delete_budget(db, budget_id, current_user.id)
