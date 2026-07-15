"""Service layer for budget operations."""
from __future__ import annotations

import math
import statistics
from datetime import datetime, date, timedelta
from typing import Optional
from collections import defaultdict

from sqlalchemy.orm import Session
from sqlalchemy import func, and_
from fastapi import HTTPException

from app.models.budget import Budget
from app.models.transaction import Transaction, TransactionType
from app.models.category import Category
from app.schemas.budget import (
    BudgetResponse,
    BudgetSummaryResponse,
    BudgetAlert,
    BudgetSuggestion,
    BudgetSuggestionsResponse,
)
from app.services.currency_helper import get_dominant_currency, get_currency_symbol


def _get_period_date_range(period: str) -> tuple[datetime, datetime]:
    """Get start and end dates for the current period."""
    today = date.today()

    if period == "weekly":
        start = today - timedelta(days=today.weekday())
        end = start + timedelta(days=6)
    elif period == "yearly":
        start = date(today.year, 1, 1)
        end = date(today.year, 12, 31)
    else:  # monthly
        start = date(today.year, today.month, 1)
        if today.month == 12:
            end = date(today.year + 1, 1, 1) - timedelta(days=1)
        else:
            end = date(today.year, today.month + 1, 1) - timedelta(days=1)

    return (
        datetime(start.year, start.month, start.day),
        datetime(end.year, end.month, end.day, 23, 59, 59),
    )


def _get_days_remaining_in_period(period: str) -> int:
    """Get the number of days remaining in the current period."""
    today = date.today()
    _, end = _get_period_date_range(period)
    remaining = (end.date() - today).days
    return max(remaining, 0)


def _get_days_elapsed_in_period(period: str) -> int:
    """Get the number of days elapsed in the current period."""
    today = date.today()
    start, _ = _get_period_date_range(period)
    elapsed = (today - start.date()).days + 1
    return max(elapsed, 1)


def _get_total_days_in_period(period: str) -> int:
    """Get total days in the current period."""
    start, end = _get_period_date_range(period)
    return (end.date() - start.date()).days + 1


def _calculate_spent(
    db: Session, user_id: int, category_id: Optional[int], period: str
) -> float:
    """Calculate total spent for a category in the current period."""
    start, end = _get_period_date_range(period)

    query = db.query(func.coalesce(func.sum(Transaction.amount), 0)).filter(
        and_(
            Transaction.user_id == user_id,
            Transaction.transaction_type == TransactionType.DEBIT,
            Transaction.date >= start,
            Transaction.date <= end,
        )
    )

    if category_id is not None:
        query = query.filter(Transaction.category_id == category_id)

    result = query.scalar()
    return float(result) if result else 0.0


def _budget_to_response(db: Session, budget: Budget, user_id: int) -> BudgetResponse:
    """Convert a Budget model to BudgetResponse with computed fields."""
    spent = _calculate_spent(db, user_id, budget.category_id, budget.period)
    remaining = budget.amount - spent
    percentage_used = (spent / budget.amount * 100) if budget.amount > 0 else 0

    category_name = None
    if budget.category_id:
        category = db.query(Category).filter(Category.id == budget.category_id).first()
        if category:
            category_name = category.name

    return BudgetResponse(
        id=budget.id,
        category_name=category_name,
        amount=round(budget.amount, 2),
        period=budget.period,
        spent=round(spent, 2),
        remaining=round(remaining, 2),
        percentage_used=round(percentage_used, 1),
        is_over_budget=spent > budget.amount,
        is_active=budget.is_active,
    )


def create_budget(
    db: Session, user_id: int, category_name: Optional[str], amount: float, period: str
) -> BudgetResponse:
    """Create a new budget for a user."""
    category_id = None
    if category_name:
        category = (
            db.query(Category)
            .filter(
                and_(
                    Category.name == category_name,
                    (Category.user_id == user_id) | (Category.is_system == True),
                )
            )
            .first()
        )
        if not category:
            raise HTTPException(status_code=404, detail=f"Category '{category_name}' not found")
        category_id = category.id

    existing = (
        db.query(Budget)
        .filter(
            and_(
                Budget.user_id == user_id,
                Budget.category_id == category_id,
                Budget.is_active == True,
            )
        )
        .first()
    )
    if existing:
        label = category_name or "Overall"
        raise HTTPException(
            status_code=409,
            detail=f"An active budget for '{label}' already exists. Update it instead.",
        )

    budget = Budget(
        user_id=user_id,
        category_id=category_id,
        amount=amount,
        period=period,
        is_active=True,
    )
    db.add(budget)
    db.commit()
    db.refresh(budget)

    return _budget_to_response(db, budget, user_id)


def get_budgets(db: Session, user_id: int) -> list[BudgetResponse]:
    """Get all active budgets with current spending for a user."""
    budgets = (
        db.query(Budget)
        .filter(and_(Budget.user_id == user_id, Budget.is_active == True))
        .order_by(Budget.created_at.desc())
        .all()
    )

    return [_budget_to_response(db, b, user_id) for b in budgets]


def get_budget_summary(db: Session, user_id: int) -> BudgetSummaryResponse:
    """Get an overview of all budgets with alerts."""
    # Get user's dominant currency for formatting
    dominant_currency = get_dominant_currency(db, user_id)
    currency_symbol = get_currency_symbol(dominant_currency)

    budget_responses = get_budgets(db, user_id)

    total_budget = sum(b.amount for b in budget_responses)
    total_spent = sum(b.spent for b in budget_responses)
    total_remaining = total_budget - total_spent
    total_percentage = (total_spent / total_budget * 100) if total_budget > 0 else 0

    primary_period = "monthly"
    if budget_responses:
        primary_period = budget_responses[0].period

    days_remaining = _get_days_remaining_in_period(primary_period)
    days_elapsed = _get_days_elapsed_in_period(primary_period)
    total_days = _get_total_days_in_period(primary_period)

    if days_elapsed > 0:
        daily_rate = total_spent / days_elapsed
        projected_spend = daily_rate * total_days
    else:
        projected_spend = total_spent

    alerts: list[BudgetAlert] = []
    for b in budget_responses:
        if b.is_over_budget:
            over_amount = b.spent - b.amount
            alerts.append(
                BudgetAlert(
                    budget_id=b.id,
                    category_name=b.category_name,
                    message=f"{currency_symbol}{over_amount:,.0f} over budget!",
                    severity="over",
                    percentage_used=b.percentage_used,
                )
            )
        elif b.percentage_used >= 90:
            alerts.append(
                BudgetAlert(
                    budget_id=b.id,
                    category_name=b.category_name,
                    message=f"Almost at limit ({b.percentage_used:.0f}% used)",
                    severity="danger",
                    percentage_used=b.percentage_used,
                )
            )
        elif b.percentage_used >= 70:
            alerts.append(
                BudgetAlert(
                    budget_id=b.id,
                    category_name=b.category_name,
                    message=f"Approaching limit ({b.percentage_used:.0f}% used)",
                    severity="warning",
                    percentage_used=b.percentage_used,
                )
            )

    alerts.sort(key=lambda a: a.percentage_used, reverse=True)

    return BudgetSummaryResponse(
        total_budget=round(total_budget, 2),
        total_spent=round(total_spent, 2),
        total_remaining=round(total_remaining, 2),
        total_percentage_used=round(total_percentage, 1),
        days_remaining_in_period=days_remaining,
        projected_end_of_period_spend=round(projected_spend, 2),
        budgets=budget_responses,
        alerts=alerts,
    )


def update_budget(
    db: Session, budget_id: int, user_id: int, updates: dict
) -> BudgetResponse:
    """Update a budget's amount, period, or active status."""
    budget = (
        db.query(Budget)
        .filter(and_(Budget.id == budget_id, Budget.user_id == user_id))
        .first()
    )
    if not budget:
        raise HTTPException(status_code=404, detail="Budget not found")

    for key, value in updates.items():
        if value is not None:
            setattr(budget, key, value)

    db.commit()
    db.refresh(budget)

    return _budget_to_response(db, budget, user_id)


def delete_budget(db: Session, budget_id: int, user_id: int) -> None:
    """Delete a budget."""
    budget = (
        db.query(Budget)
        .filter(and_(Budget.id == budget_id, Budget.user_id == user_id))
        .first()
    )
    if not budget:
        raise HTTPException(status_code=404, detail="Budget not found")

    db.delete(budget)
    db.commit()


def suggest_budgets(db: Session, user_id: int) -> BudgetSuggestionsResponse:
    """Generate smart AI-driven budget suggestions using trend analysis, outlier detection,
    and consistency scoring.

    Analyzes all transaction history to generate per-category suggestions with:
    - Linear regression trend projection
    - Outlier removal via IQR
    - Consistency-based buffer sizing
    - Income-aware 50/30/20 distribution caps
    - Human-readable rationale for each suggestion
    """
    # Get user's dominant currency for formatting
    dominant_currency = get_dominant_currency(db, user_id)
    currency_symbol = get_currency_symbol(dominant_currency)

    all_tx = (
        db.query(Transaction.date, Transaction.amount, Transaction.category_id)
        .filter(
            and_(
                Transaction.user_id == user_id,
                Transaction.transaction_type == TransactionType.DEBIT,
            )
        )
        .all()
    )

    if not all_tx:
        return BudgetSuggestionsResponse(suggestions=[])

    dates = [tx.date for tx in all_tx]
    earliest_date = min(dates)
    latest_date = max(dates)

    months_span = (latest_date.year - earliest_date.year) * 12 + (latest_date.month - earliest_date.month)
    months_span = max(1, months_span)

    # Build per-category monthly spending breakdown
    category_monthly: dict[int | None, dict[str, float]] = defaultdict(lambda: defaultdict(float))
    for tx in all_tx:
        month_key = f"{tx.date.year}-{tx.date.month:02d}"
        category_monthly[tx.category_id][month_key] = (
            category_monthly[tx.category_id].get(month_key, 0.0) + tx.amount
        )

    # Resolve category names
    category_ids = [cid for cid in category_monthly.keys() if cid is not None]
    category_name_map: dict[int | None, str] = {None: "Uncategorized"}
    if category_ids:
        cats = db.query(Category.id, Category.name).filter(Category.id.in_(category_ids)).all()
        for cat in cats:
            category_name_map[cat.id] = cat.name

    # Get income data for 50/30/20 rule
    avg_monthly_income = _get_avg_monthly_income(db, user_id, months_span)

    # Category classification for 50/30/20 rule
    needs_categories = {"Food & Dining", "Utilities", "Rent", "Healthcare", "Transportation", "EMI", "Insurance", "Groceries"}
    wants_categories = {"Entertainment", "Shopping", "Dining Out", "Subscriptions", "Travel", "Lifestyle"}

    suggestions: list[BudgetSuggestion] = []

    for category_id, monthly_data in category_monthly.items():
        category_name = category_name_map.get(category_id, "Uncategorized")

        # Build chronological monthly amounts
        all_months = sorted(monthly_data.keys())
        monthly_amounts = [monthly_data[m] for m in all_months]
        num_months = len(monthly_amounts)

        if num_months == 0 or sum(monthly_amounts) <= 0:
            continue

        # --- Outlier Detection (IQR method) ---
        clean_amounts, has_outliers = _remove_outliers_iqr(monthly_amounts)

        # --- Trend Analysis (linear regression on clean data) ---
        trend_direction, slope, projected_next = _calculate_trend(clean_amounts)

        # --- Consistency Analysis ---
        consistency_score, is_consistent = _calculate_consistency(clean_amounts)

        # --- Select methodology & compute suggestion ---
        suggestion_amount, methodology, confidence = _select_methodology(
            clean_amounts=clean_amounts,
            projected_next=projected_next,
            trend_direction=trend_direction,
            is_consistent=is_consistent,
            has_outliers=has_outliers,
            category_name=category_name,
            avg_monthly_income=avg_monthly_income,
            needs_categories=needs_categories,
            wants_categories=wants_categories,
        )

        avg_spend = statistics.mean(clean_amounts)

        # --- Generate Rationale ---
        rationale = _generate_rationale(
            category_name=category_name,
            methodology=methodology,
            avg_spend=avg_spend,
            suggestion_amount=suggestion_amount,
            trend_direction=trend_direction,
            slope=slope,
            is_consistent=is_consistent,
            has_outliers=has_outliers,
            num_months=num_months,
            currency_symbol=currency_symbol,
        )

        # Round suggestion to nearest 100 for amounts > 1000, nearest 10 otherwise
        if suggestion_amount >= 1000:
            suggestion_amount = round(suggestion_amount / 100) * 100
        else:
            suggestion_amount = round(suggestion_amount / 10) * 10

        suggestion_amount = max(suggestion_amount, 100.0)

        suggestions.append(
            BudgetSuggestion(
                category_name=category_name,
                suggested_amount=round(suggestion_amount, 2),
                confidence=round(confidence, 2),
                rationale=rationale,
                methodology=methodology,
                avg_monthly_spend=round(avg_spend, 2),
                trend=trend_direction,
                months_analyzed=num_months,
                average_spending=round(avg_spend, 2),
                reasoning=rationale,
            )
        )

    suggestions.sort(key=lambda s: s.avg_monthly_spend, reverse=True)

    return BudgetSuggestionsResponse(suggestions=suggestions)


def _get_avg_monthly_income(db: Session, user_id: int, months_span: int) -> float:
    """Get average monthly income for 50/30/20 calculations."""
    total_income = (
        db.query(func.coalesce(func.sum(Transaction.amount), 0))
        .filter(
            and_(
                Transaction.user_id == user_id,
                Transaction.transaction_type == TransactionType.CREDIT,
            )
        )
        .scalar()
    )
    return float(total_income) / max(1, months_span)


def _percentile(data: list[float], pct: float) -> float:
    """Calculate percentile using linear interpolation."""
    sorted_data = sorted(data)
    n = len(sorted_data)
    if n == 1:
        return sorted_data[0]
    k = (n - 1) * (pct / 100.0)
    f = math.floor(k)
    c = math.ceil(k)
    if f == c:
        return sorted_data[int(k)]
    return sorted_data[f] * (c - k) + sorted_data[c] * (k - f)


def _remove_outliers_iqr(amounts: list[float]) -> tuple[list[float], bool]:
    """Remove outlier months using IQR method. Returns (clean_data, had_outliers)."""
    if len(amounts) < 4:
        return amounts, False

    q1 = _percentile(amounts, 25)
    q3 = _percentile(amounts, 75)
    iqr = q3 - q1

    if iqr == 0:
        return amounts, False

    lower_bound = q1 - 1.5 * iqr
    upper_bound = q3 + 1.5 * iqr

    clean = [x for x in amounts if lower_bound <= x <= upper_bound]

    if len(clean) == 0:
        return amounts, False

    had_outliers = len(clean) < len(amounts)
    return clean, had_outliers


def _calculate_trend(amounts: list[float]) -> tuple[str, float, float]:
    """Calculate spending trend using linear regression.

    Returns: (direction, slope, projected_next_month_value)
    """
    n = len(amounts)
    if n < 2:
        return "stable", 0.0, amounts[0] if n == 1 else 0.0

    x = list(range(n))
    y = amounts

    x_mean = sum(x) / n
    y_mean = sum(y) / n
    numerator = sum((xi - x_mean) * (yi - y_mean) for xi, yi in zip(x, y))
    denominator = sum((xi - x_mean) ** 2 for xi in x)

    if denominator == 0:
        return "stable", 0.0, y_mean

    slope = numerator / denominator
    intercept = y_mean - slope * x_mean

    projected = slope * n + intercept
    projected = max(projected, 0.0)

    avg_val = y_mean if y_mean > 0 else 1.0
    relative_slope = slope / avg_val

    if relative_slope > 0.05:
        direction = "increasing"
    elif relative_slope < -0.05:
        direction = "decreasing"
    else:
        direction = "stable"

    return direction, slope, projected


def _calculate_consistency(amounts: list[float]) -> tuple[float, bool]:
    """Compute a consistency score (coefficient of variation).

    Returns: (cv_score, is_consistent) where is_consistent means low variance.
    """
    if len(amounts) < 2:
        return 0.0, True

    mean_val = statistics.mean(amounts)
    if mean_val == 0:
        return 0.0, True

    std_val = statistics.pstdev(amounts)
    cv = std_val / mean_val

    is_consistent = cv < 0.25
    return cv, is_consistent


def _select_methodology(
    clean_amounts: list[float],
    projected_next: float,
    trend_direction: str,
    is_consistent: bool,
    has_outliers: bool,
    category_name: str,
    avg_monthly_income: float,
    needs_categories: set[str],
    wants_categories: set[str],
) -> tuple[float, str, float]:
    """Select the best methodology and compute suggestion amount.

    Returns: (suggested_amount, methodology_name, confidence)
    """
    mean_spend = statistics.mean(clean_amounts)
    median_spend = statistics.median(clean_amounts)
    n = len(clean_amounts)

    # Strategy 1: Consistency-based (for very stable categories)
    if is_consistent and n >= 3 and not has_outliers:
        suggestion = mean_spend * 1.05
        return suggestion, "consistency_based", min(0.92, 0.7 + n * 0.03)

    # Strategy 2: Trend projection (for categories with clear trends)
    if trend_direction in ("increasing", "decreasing") and n >= 3:
        if trend_direction == "increasing":
            suggestion = projected_next
        else:
            suggestion = projected_next * 1.10
        # Clamp: don't suggest less than median or more than 2x median
        suggestion = max(suggestion, median_spend * 0.8)
        suggestion = min(suggestion, median_spend * 2.0)
        confidence = min(0.85, 0.6 + n * 0.03)
        return suggestion, "trend_projection", confidence

    # Strategy 3: Median with buffer (when outliers detected or volatile)
    if has_outliers or not is_consistent:
        buffer = 1.20 if not is_consistent else 1.10
        suggestion = median_spend * buffer
        confidence = min(0.78, 0.5 + n * 0.04)
        return suggestion, "median_with_buffer", confidence

    # Strategy 4: 50/30/20 rule cap (income-aware)
    if avg_monthly_income > 0:
        cap = _get_fifty_thirty_twenty_cap(
            category_name, avg_monthly_income, needs_categories, wants_categories
        )
        if cap is not None and mean_spend > cap:
            return cap, "fifty_thirty_twenty", 0.70

    # Default: median + 10% buffer
    suggestion = median_spend * 1.10
    confidence = min(0.75, 0.5 + n * 0.03)
    return suggestion, "median_with_buffer", confidence


def _get_fifty_thirty_twenty_cap(
    category_name: str,
    avg_monthly_income: float,
    needs_categories: set[str],
    wants_categories: set[str],
) -> float | None:
    """Calculate the 50/30/20 spending cap for a category."""
    if category_name in needs_categories:
        # 50% of income for needs, distributed proportionally (rough cap per category)
        return avg_monthly_income * 0.50 * 0.25
    elif category_name in wants_categories:
        # 30% of income for wants
        return avg_monthly_income * 0.30 * 0.30
    return None


def _generate_rationale(
    category_name: str,
    methodology: str,
    avg_spend: float,
    suggestion_amount: float,
    trend_direction: str,
    slope: float,
    is_consistent: bool,
    has_outliers: bool,
    num_months: int,
    currency_symbol: str,
) -> str:
    """Generate a human-readable rationale for the budget suggestion."""
    period_str = f"{num_months} month{'s' if num_months > 1 else ''}"

    if methodology == "consistency_based":
        return (
            f"{currency_symbol}{suggestion_amount:,.0f}/mo — Based on {period_str} of consistent "
            f"spending averaging {currency_symbol}{avg_spend:,.0f}. 5% buffer added."
        )

    if methodology == "trend_projection":
        if trend_direction == "increasing":
            pct_change = abs(slope / avg_spend * 100) if avg_spend > 0 else 0
            return (
                f"{currency_symbol}{suggestion_amount:,.0f}/mo — Trending upward "
                f"(+{pct_change:.0f}% slope). Suggested budget caps the increase."
            )
        else:
            return (
                f"{currency_symbol}{suggestion_amount:,.0f}/mo — Trending downward. "
                f"Projected spend + 10% buffer rewards the reduction."
            )

    if methodology == "median_with_buffer":
        if has_outliers:
            return (
                f"{currency_symbol}{suggestion_amount:,.0f}/mo — Outlier months detected and excluded. "
                f"Based on median spending with buffer for flexibility."
            )
        return (
            f"{currency_symbol}{suggestion_amount:,.0f}/mo — Variable category "
            f"(high month-to-month variance). Includes 20% buffer for flexibility."
        )

    if methodology == "fifty_thirty_twenty":
        return (
            f"{currency_symbol}{suggestion_amount:,.0f}/mo — Capped using 50/30/20 income rule. "
            f"Current avg {currency_symbol}{avg_spend:,.0f} exceeds recommended allocation."
        )

    return f"{currency_symbol}{suggestion_amount:,.0f}/mo — Based on {period_str} of data."
