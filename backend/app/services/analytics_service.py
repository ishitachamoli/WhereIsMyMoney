"""Service layer for analytics operations."""
from __future__ import annotations

from sqlalchemy.orm import Session
from sqlalchemy import func, and_, case, desc
from datetime import datetime
from typing import Optional

from app.models.transaction import Transaction, TransactionType
from app.models.category import Category
from app.schemas.analytics import (
    SpendingByCategory,
    TimelineEntry,
    IncomeVsExpenseEntry,
    FinancialSummary,
    CategoryAnalyticsResponse,
    CategorySummary,
    DailySpendingEntry,
    MonthlySpendingEntry,
    TopTransactionEntry,
    IncomeTimelineEntry,
    IncomeSourceEntry,
)


def get_spending_by_category(
    db: Session,
    user_id: int,
    start_date: Optional[datetime] = None,
    end_date: Optional[datetime] = None,
) -> list[SpendingByCategory]:
    """Get spending grouped by category for debit transactions."""
    query = db.query(
        Transaction.category_id,
        func.coalesce(Category.name, "Uncategorized").label("category_name"),
        func.sum(Transaction.amount).label("total_amount"),
        func.count(Transaction.id).label("transaction_count"),
    ).outerjoin(Category, Transaction.category_id == Category.id).filter(
        and_(
            Transaction.user_id == user_id,
            Transaction.transaction_type == TransactionType.DEBIT,
        )
    )

    if start_date:
        query = query.filter(Transaction.date >= start_date)
    if end_date:
        query = query.filter(Transaction.date <= end_date)

    results = query.group_by(Transaction.category_id, Category.name).all()

    total_spending = sum(r.total_amount for r in results) if results else 0

    return [
        SpendingByCategory(
            category=r.category_name,
            total_amount=round(r.total_amount, 2),
            transaction_count=r.transaction_count,
            percentage=round((r.total_amount / total_spending * 100), 2) if total_spending > 0 else 0,
            average_transaction=round(r.total_amount / r.transaction_count, 2) if r.transaction_count > 0 else 0,
        )
        for r in results
    ]


def _get_period_expression(db: Session, granularity: str):
    """Get database-agnostic period expression for grouping."""
    dialect = db.bind.dialect.name if db.bind else "sqlite"

    if dialect == "postgresql":
        if granularity == "daily":
            return func.to_char(Transaction.date, "YYYY-MM-DD")
        elif granularity == "weekly":
            return func.to_char(Transaction.date, "IYYY-IW")
        else:
            return func.to_char(Transaction.date, "YYYY-MM")
    else:
        if granularity == "daily":
            return func.strftime("%Y-%m-%d", Transaction.date)
        elif granularity == "weekly":
            return func.strftime("%Y-W%W", Transaction.date)
        else:
            return func.strftime("%Y-%m", Transaction.date)


def get_timeline(
    db: Session,
    user_id: int,
    granularity: str = "monthly",
    start_date: Optional[datetime] = None,
    end_date: Optional[datetime] = None,
    months: Optional[int] = None,
) -> list[TimelineEntry]:
    """Get income/expense timeline grouped by period."""
    period_expr = _get_period_expression(db, granularity)

    query = db.query(
        period_expr.label("period"),
        func.sum(
            case(
                (Transaction.transaction_type == TransactionType.CREDIT, Transaction.amount),
                else_=0,
            )
        ).label("total_credits"),
        func.sum(
            case(
                (Transaction.transaction_type == TransactionType.DEBIT, Transaction.amount),
                else_=0,
            )
        ).label("total_debits"),
        func.count(Transaction.id).label("transaction_count"),
    ).filter(Transaction.user_id == user_id)

    if start_date:
        query = query.filter(Transaction.date >= start_date)
    if end_date:
        query = query.filter(Transaction.date <= end_date)

    results = query.group_by("period").order_by("period").all()

    if months and len(results) > months:
        results = results[-months:]

    return [
        TimelineEntry(
            month=r.period,
            income=round(r.total_credits, 2),
            expenses=round(r.total_debits, 2),
            net=round(r.total_credits - r.total_debits, 2),
            transaction_count=r.transaction_count,
            savings_rate=round(
                ((r.total_credits - r.total_debits) / r.total_credits * 100), 2
            ) if r.total_credits > 0 else 0,
        )
        for r in results
    ]


def get_income_vs_expenses(
    db: Session,
    user_id: int,
    start_date: Optional[datetime] = None,
    end_date: Optional[datetime] = None,
    months: Optional[int] = None,
) -> list[IncomeVsExpenseEntry]:
    """Get per-month income vs expenses data."""
    period_expr = _get_period_expression(db, "monthly")

    query = db.query(
        period_expr.label("period"),
        func.sum(
            case(
                (Transaction.transaction_type == TransactionType.CREDIT, Transaction.amount),
                else_=0,
            )
        ).label("total_credits"),
        func.sum(
            case(
                (Transaction.transaction_type == TransactionType.DEBIT, Transaction.amount),
                else_=0,
            )
        ).label("total_debits"),
    ).filter(Transaction.user_id == user_id)

    if start_date:
        query = query.filter(Transaction.date >= start_date)
    if end_date:
        query = query.filter(Transaction.date <= end_date)

    results = query.group_by("period").order_by("period").all()

    if months and len(results) > months:
        results = results[-months:]

    return [
        IncomeVsExpenseEntry(
            month=r.period,
            income=round(r.total_credits, 2),
            expenses=round(r.total_debits, 2),
        )
        for r in results
    ]


def get_summary(
    db: Session,
    user_id: int,
    start_date: Optional[datetime] = None,
    end_date: Optional[datetime] = None,
) -> FinancialSummary:
    """Get financial summary matching frontend FinancialSummary type."""
    query = db.query(
        func.sum(
            case(
                (Transaction.transaction_type == TransactionType.CREDIT, Transaction.amount),
                else_=0,
            )
        ).label("total_income"),
        func.sum(
            case(
                (Transaction.transaction_type == TransactionType.DEBIT, Transaction.amount),
                else_=0,
            )
        ).label("total_expenses"),
        func.count(Transaction.id).label("transaction_count"),
        func.min(Transaction.date).label("min_date"),
        func.max(Transaction.date).label("max_date"),
    ).filter(Transaction.user_id == user_id)

    if start_date:
        query = query.filter(Transaction.date >= start_date)
    if end_date:
        query = query.filter(Transaction.date <= end_date)

    result = query.first()

    total_income = round(result.total_income or 0, 2)
    total_expenses = round(result.total_expenses or 0, 2)
    net_savings = round(total_income - total_expenses, 2)
    savings_rate = round((net_savings / total_income * 100), 2) if total_income > 0 else 0

    # Find top spending category
    top_category_query = db.query(
        func.coalesce(Category.name, "Uncategorized").label("category_name"),
        func.sum(Transaction.amount).label("total_amount"),
    ).outerjoin(Category, Transaction.category_id == Category.id).filter(
        and_(
            Transaction.user_id == user_id,
            Transaction.transaction_type == TransactionType.DEBIT,
        )
    )

    if start_date:
        top_category_query = top_category_query.filter(Transaction.date >= start_date)
    if end_date:
        top_category_query = top_category_query.filter(Transaction.date <= end_date)

    top_categories = (
        top_category_query
        .group_by(Category.name)
        .order_by(func.sum(Transaction.amount).desc())
        .first()
    )

    top_category = top_categories.category_name if top_categories else "N/A"
    top_category_amount = round(top_categories.total_amount, 2) if top_categories else 0

    date_start = result.min_date.isoformat() if result.min_date else ""
    date_end = result.max_date.isoformat() if result.max_date else ""

    return FinancialSummary(
        total_income=total_income,
        total_expenses=total_expenses,
        net_savings=net_savings,
        savings_rate=savings_rate,
        top_category=top_category,
        top_category_amount=top_category_amount,
        transaction_count=result.transaction_count or 0,
        date_range={"start": date_start, "end": date_end},
    )


def get_category_analytics(
    db: Session,
    user_id: int,
    category_name: str,
    start_date: Optional[datetime] = None,
    end_date: Optional[datetime] = None,
) -> CategoryAnalyticsResponse:
    """Get deep-dive analytics for a specific category."""
    dialect = db.bind.dialect.name if db.bind else "sqlite"

    # Base filter: user's debit transactions in this category
    base_filter = and_(
        Transaction.user_id == user_id,
        Transaction.transaction_type == TransactionType.DEBIT,
    )

    # Join category and filter by name
    base_query = db.query(Transaction).outerjoin(
        Category, Transaction.category_id == Category.id
    ).filter(base_filter)

    if category_name.lower() == "uncategorized":
        base_query = base_query.filter(Transaction.category_id.is_(None))
    else:
        base_query = base_query.filter(Category.name == category_name)

    if start_date:
        base_query = base_query.filter(Transaction.date >= start_date)
    if end_date:
        base_query = base_query.filter(Transaction.date <= end_date)

    # Daily spending
    if dialect == "postgresql":
        day_expr = func.to_char(Transaction.date, "YYYY-MM-DD")
    else:
        day_expr = func.strftime("%Y-%m-%d", Transaction.date)

    daily_query = db.query(
        day_expr.label("day"),
        func.sum(Transaction.amount).label("total"),
    ).outerjoin(Category, Transaction.category_id == Category.id).filter(base_filter)

    if category_name.lower() == "uncategorized":
        daily_query = daily_query.filter(Transaction.category_id.is_(None))
    else:
        daily_query = daily_query.filter(Category.name == category_name)

    if start_date:
        daily_query = daily_query.filter(Transaction.date >= start_date)
    if end_date:
        daily_query = daily_query.filter(Transaction.date <= end_date)

    daily_results = daily_query.group_by("day").order_by("day").all()

    daily_spending = [
        DailySpendingEntry(date=r.day, amount=round(r.total, 2))
        for r in daily_results
    ]

    # Monthly spending
    if dialect == "postgresql":
        month_expr = func.to_char(Transaction.date, "YYYY-MM")
    else:
        month_expr = func.strftime("%Y-%m", Transaction.date)

    monthly_query = db.query(
        month_expr.label("month"),
        func.sum(Transaction.amount).label("total"),
    ).outerjoin(Category, Transaction.category_id == Category.id).filter(base_filter)

    if category_name.lower() == "uncategorized":
        monthly_query = monthly_query.filter(Transaction.category_id.is_(None))
    else:
        monthly_query = monthly_query.filter(Category.name == category_name)

    if start_date:
        monthly_query = monthly_query.filter(Transaction.date >= start_date)
    if end_date:
        monthly_query = monthly_query.filter(Transaction.date <= end_date)

    monthly_results = monthly_query.group_by("month").order_by("month").all()

    monthly_spending = []
    for i, r in enumerate(monthly_results):
        prev_amount = monthly_results[i - 1].total if i > 0 else None
        change_pct = None
        if prev_amount is not None and prev_amount > 0:
            change_pct = round(((r.total - prev_amount) / prev_amount) * 100, 1)
        monthly_spending.append(
            MonthlySpendingEntry(month=r.month, amount=round(r.total, 2), change_pct=change_pct)
        )

    # Top transactions (top 10 by amount)
    top_txns = base_query.order_by(desc(Transaction.amount)).limit(10).all()
    top_transactions = [
        TopTransactionEntry(
            date=t.date.strftime("%Y-%m-%d") if t.date else "",
            description=t.description or "",
            amount=round(t.amount, 2),
        )
        for t in top_txns
    ]

    # Summary
    total_in_category = sum(r.total for r in monthly_results) if monthly_results else 0
    num_months = len(monthly_results) if monthly_results else 1
    avg_monthly = total_in_category / num_months if num_months > 0 else 0

    # Total overall expenses for percentage calculation
    overall_expenses_result = db.query(
        func.sum(Transaction.amount)
    ).filter(
        and_(
            Transaction.user_id == user_id,
            Transaction.transaction_type == TransactionType.DEBIT,
        )
    ).scalar() or 0

    pct_of_total = (total_in_category / overall_expenses_result * 100) if overall_expenses_result > 0 else 0

    count = base_query.count()

    # Trend: compare last 3 months vs prior 3 months
    trend = "stable"
    if len(monthly_results) >= 6:
        recent_3 = sum(r.total for r in monthly_results[-3:])
        prior_3 = sum(r.total for r in monthly_results[-6:-3])
        if prior_3 > 0:
            change = (recent_3 - prior_3) / prior_3
            if change > 0.1:
                trend = "increasing"
            elif change < -0.1:
                trend = "decreasing"
    elif len(monthly_results) >= 2:
        if monthly_results[-1].total > monthly_results[-2].total * 1.1:
            trend = "increasing"
        elif monthly_results[-1].total < monthly_results[-2].total * 0.9:
            trend = "decreasing"

    summary = CategorySummary(
        total=round(total_in_category, 2),
        avg_monthly=round(avg_monthly, 2),
        pct_of_total=round(pct_of_total, 2),
        count=count,
        trend=trend,
    )

    return CategoryAnalyticsResponse(
        category=category_name,
        daily_spending=daily_spending,
        monthly_spending=monthly_spending,
        top_transactions=top_transactions,
        summary=summary,
    )


def _categorize_income_source(description: str) -> str:
    """Categorize income by transaction description patterns."""
    desc_lower = description.lower()

    # Salary/payroll patterns
    if any(keyword in desc_lower for keyword in ['salary', 'payroll', 'pay', 'wage', 'compensation']):
        return 'Salary'

    # Investment returns
    if any(keyword in desc_lower for keyword in ['dividend', 'interest', 'investment', 'mutual', 'stock', 'capital gain']):
        return 'Investments'

    # Transfer/repayment
    if any(keyword in desc_lower for keyword in ['transfer', 'refund', 'reimbursement', 'cashback', 'reward']):
        return 'Transfers & Refunds'

    # Other income
    return 'Other Income'


def get_income_timeline(
    db: Session,
    user_id: int,
    start_date: Optional[datetime] = None,
    end_date: Optional[datetime] = None,
    months: Optional[int] = None,
) -> list[IncomeTimelineEntry]:
    """Get monthly income with breakdown by source."""
    period_expr = _get_period_expression(db, "monthly")

    # Get all credit transactions grouped by month
    query = db.query(
        period_expr.label("month"),
        Transaction.description,
        func.sum(Transaction.amount).label("total"),
    ).filter(
        and_(
            Transaction.user_id == user_id,
            Transaction.transaction_type == TransactionType.CREDIT,
        )
    )

    if start_date:
        query = query.filter(Transaction.date >= start_date)
    if end_date:
        query = query.filter(Transaction.date <= end_date)

    results = query.group_by("month", Transaction.description).order_by("month").all()

    # Group by month and source
    monthly_data = {}
    for row in results:
        month = row.month
        if month not in monthly_data:
            monthly_data[month] = {}

        source = _categorize_income_source(row.description)
        if source not in monthly_data[month]:
            monthly_data[month][source] = 0

        monthly_data[month][source] += row.total

    # Build timeline entries with month-over-month change
    timeline_entries = []
    months_list = sorted(monthly_data.keys())

    if months and len(months_list) > months:
        months_list = months_list[-months:]

    for i, month in enumerate(months_list):
        month_total = sum(monthly_data[month].values())

        # Calculate month-over-month change
        change_pct = None
        if i > 0:
            prev_month = months_list[i - 1]
            prev_total = sum(monthly_data[prev_month].values())
            if prev_total > 0:
                change_pct = round(((month_total - prev_total) / prev_total) * 100, 1)

        # Build income sources list
        sources = [
            IncomeSourceEntry(name=source, amount=round(amount, 2))
            for source, amount in sorted(monthly_data[month].items(), key=lambda x: x[1], reverse=True)
        ]

        timeline_entries.append(
            IncomeTimelineEntry(
                month=month,
                amount=round(month_total, 2),
                change_pct=change_pct,
                sources=sources,
            )
        )

    return timeline_entries
