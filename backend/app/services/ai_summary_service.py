"""AI-powered financial summary service.

Generates structured financial insights from transaction data using
template-based analysis (always works, no ML required).
"""

from __future__ import annotations

import logging
from collections import defaultdict
from datetime import datetime, timedelta, timezone
from typing import Optional

from sqlalchemy.orm import Session

from app.models.transaction import Transaction, TransactionType
from app.services.currency_helper import get_dominant_currency, get_currency_symbol
from app.services import tone_templates as tones

logger = logging.getLogger(__name__)


def generate_summary(user_id: int, db: Session) -> dict:
    """Generate a comprehensive financial summary for a user.

    Args:
        user_id: The user to generate summary for.
        db: Database session.

    Returns:
        Structured JSON with sections: overview, habits, insights, advice,
        monthly_review, fun_statistics, spending_personality, detailed_insights,
        achievements, predictions.
    """
    all_txns = (
        db.query(Transaction)
        .filter(Transaction.user_id == user_id)
        .order_by(Transaction.date.desc())
        .all()
    )

    if not all_txns:
        return _empty_summary()

    # Use latest transaction date as reference point, not today's date
    # This ensures "last 30 days" analysis uses actual data, not calendar days
    reference_date = all_txns[0].date
    
    # Keep actual timestamp for when summary was generated
    now = datetime.now(timezone.utc)
    
    # Calculate date ranges relative to the latest transaction
    thirty_days_ago = reference_date - timedelta(days=30)
    sixty_days_ago = reference_date - timedelta(days=60)
    current_month_start = reference_date.replace(day=1, hour=0, minute=0, second=0, microsecond=0)
    last_month_start = (current_month_start - timedelta(days=1)).replace(day=1)
    
    # Format month names for display
    current_month_name = reference_date.strftime("%B %Y")
    last_month_name = (reference_date.replace(day=1) - timedelta(days=1)).strftime("%B %Y")
    next_month_date = (reference_date.replace(day=1) + timedelta(days=32)).replace(day=1)
    next_month_name = next_month_date.strftime("%B %Y")

    current_month_txns = [t for t in all_txns if t.date and t.date >= current_month_start]
    last_month_txns = [
        t for t in all_txns
        if t.date and last_month_start <= t.date < current_month_start
    ]
    last_30_txns = [t for t in all_txns if t.date and t.date >= thirty_days_ago]
    prev_30_txns = [t for t in all_txns if t.date and sixty_days_ago <= t.date < thirty_days_ago]

    total_income = sum(t.amount for t in all_txns if t.transaction_type == TransactionType.CREDIT)
    total_expenses = sum(t.amount for t in all_txns if t.transaction_type == TransactionType.DEBIT)

    current_income = sum(t.amount for t in current_month_txns if t.transaction_type == TransactionType.CREDIT)
    current_expenses = sum(t.amount for t in current_month_txns if t.transaction_type == TransactionType.DEBIT)

    last_income = sum(t.amount for t in last_month_txns if t.transaction_type == TransactionType.CREDIT)
    last_expenses = sum(t.amount for t in last_month_txns if t.transaction_type == TransactionType.DEBIT)

    savings_rate = 0.0
    if total_income > 0:
        savings_rate = round((total_income - total_expenses) / total_income * 100, 1)

    current_savings_rate = 0.0
    if current_income > 0:
        current_savings_rate = round((current_income - current_expenses) / current_income * 100, 1)

    # Category breakdowns
    category_spending = defaultdict(float)
    category_spending_last = defaultdict(float)
    category_spending_30d = defaultdict(float)
    category_spending_prev30d = defaultdict(float)

    for t in all_txns:
        if t.transaction_type == TransactionType.DEBIT and t.category:
            category_spending[t.category.name] += t.amount
    for t in last_month_txns:
        if t.transaction_type == TransactionType.DEBIT and t.category:
            category_spending_last[t.category.name] += t.amount
    for t in last_30_txns:
        if t.transaction_type == TransactionType.DEBIT and t.category:
            category_spending_30d[t.category.name] += t.amount
    for t in prev_30_txns:
        if t.transaction_type == TransactionType.DEBIT and t.category:
            category_spending_prev30d[t.category.name] += t.amount

    current_category_spending = defaultdict(float)
    for t in current_month_txns:
        if t.transaction_type == TransactionType.DEBIT and t.category:
            current_category_spending[t.category.name] += t.amount

    # Top spending category
    top_category = None
    top_category_amount = 0.0
    top_category_change = None
    if category_spending:
        top_category = max(category_spending, key=category_spending.get)
        top_category_amount = category_spending[top_category]
        if top_category in category_spending_last and category_spending_last[top_category] > 0:
            change = ((current_category_spending.get(top_category, 0) - category_spending_last[top_category])
                      / category_spending_last[top_category] * 100)
            top_category_change = round(change, 1)

    # Merchant analysis
    merchant_counts: dict[str, int] = defaultdict(int)
    merchant_totals: dict[str, float] = defaultdict(float)
    merchant_counts_30d: dict[str, int] = defaultdict(int)
    merchant_totals_30d: dict[str, float] = defaultdict(float)

    for t in all_txns:
        if t.transaction_type == TransactionType.DEBIT and t.description:
            merchant = _extract_simple_merchant(t.description)
            if merchant:
                merchant_counts[merchant] += 1
                merchant_totals[merchant] += t.amount

    for t in last_30_txns:
        if t.transaction_type == TransactionType.DEBIT and t.description:
            merchant = _extract_simple_merchant(t.description)
            if merchant:
                merchant_counts_30d[merchant] += 1
                merchant_totals_30d[merchant] += t.amount

    top_merchants = sorted(merchant_counts.items(), key=lambda x: x[1], reverse=True)[:5]

    # Anomaly detection
    anomalies = _detect_anomalies(all_txns, category_spending)

    # Recurring payments
    recurring_total = _estimate_recurring_total(all_txns)

    # Get user's dominant currency for formatting
    dominant_currency = get_dominant_currency(db, user_id)
    currency_symbol = get_currency_symbol(dominant_currency)

    # --- Build all sections ---

    overview = _build_overview(
        total_income, total_expenses, savings_rate, current_income,
        current_expenses, current_savings_rate, last_expenses, all_txns,
    )

    habits = _build_habits(
        top_category, top_category_amount, top_category_change,
        top_merchants, merchant_totals, category_spending, all_txns,
    )

    insights = _build_insights(
        anomalies, recurring_total, current_expenses, last_expenses,
        category_spending, total_expenses,
    )

    advice = _generate_advice(
        savings_rate=savings_rate,
        current_expenses=current_expenses,
        current_income=current_income,
        last_expenses=last_expenses,
        top_category=top_category,
        anomalies=anomalies,
        recurring_total=recurring_total,
    )

    monthly_review = _build_monthly_review(
        last_30_txns, prev_30_txns, category_spending_30d,
        category_spending_prev30d, merchant_counts_30d, reference_date,
        current_month_name, last_month_name, currency_symbol,
    )

    fun_statistics = _build_fun_statistics(
        last_30_txns, merchant_counts_30d, merchant_totals_30d,
        category_spending_30d, current_expenses, current_income, reference_date,
        current_month_name, currency_symbol,
    )

    spending_personality = _build_spending_personality(
        category_spending_30d, last_30_txns, current_income, current_expenses, savings_rate,
    )

    detailed_insights = _build_detailed_insights(
        last_30_txns, merchant_counts_30d, merchant_totals_30d,
        current_income, current_expenses, savings_rate,
        category_spending_30d, category_spending_prev30d, reference_date,
        current_month_name, currency_symbol,
    )

    achievements = _build_achievements(
        all_txns, savings_rate, current_savings_rate, reference_date,
        current_month_name, currency_symbol,
    )

    predictions = _build_predictions(
        current_expenses, current_income, recurring_total,
        savings_rate, reference_date, next_month_name, currency_symbol,
    )

    return {
        "overview": overview,
        "habits": habits,
        "insights": insights,
        "advice": advice,
        "monthly_review": monthly_review,
        "fun_statistics": fun_statistics,
        "spending_personality": spending_personality,
        "detailed_insights": detailed_insights,
        "achievements": achievements,
        "predictions": predictions,
        "generated_at": now.isoformat(),
        "period": {
            "start": all_txns[-1].date.isoformat() if all_txns[-1].date else None,
            "end": all_txns[0].date.isoformat() if all_txns[0].date else None,
            "reference_date": reference_date.isoformat() if reference_date else None,
            "note": "All 'last 30 days' calculations use the latest transaction date as reference, not today's date",
        },
    }


# ─── Section Builders ─────────────────────────────────────────────────────────


def _build_overview(
    total_income: float,
    total_expenses: float,
    savings_rate: float,
    current_income: float,
    current_expenses: float,
    current_savings_rate: float,
    last_expenses: float,
    all_txns: list,
) -> dict:
    return {
        "total_income": round(total_income, 2),
        "total_expenses": round(total_expenses, 2),
        "net_savings": round(total_income - total_expenses, 2),
        "savings_rate": savings_rate,
        "current_month_income": round(current_income, 2),
        "current_month_expenses": round(current_expenses, 2),
        "current_month_savings_rate": current_savings_rate,
        "last_month_expenses": round(last_expenses, 2),
        "expense_change_pct": (
            round((current_expenses - last_expenses) / last_expenses * 100, 1)
            if last_expenses > 0 else None
        ),
        "transaction_count": len(all_txns),
    }


def _build_habits(
    top_category: Optional[str],
    top_category_amount: float,
    top_category_change: Optional[float],
    top_merchants: list,
    merchant_totals: dict,
    category_spending: dict,
    all_txns: list,
) -> dict:
    debit_txns = [t for t in all_txns if t.transaction_type == TransactionType.DEBIT]
    avg_txn = round(sum(t.amount for t in debit_txns) / len(debit_txns), 2) if debit_txns else 0

    return {
        "top_category": top_category,
        "top_category_amount": round(top_category_amount, 2),
        "top_category_change_pct": top_category_change,
        "top_merchants": [
            {
                "name": name,
                "frequency": count,
                "total_spent": round(merchant_totals[name], 2),
            }
            for name, count in top_merchants
        ],
        "categories_used": len(category_spending),
        "average_transaction": avg_txn,
    }


def _build_insights(
    anomalies: list,
    recurring_total: float,
    current_expenses: float,
    last_expenses: float,
    category_spending: dict,
    total_expenses: float,
) -> dict:
    return {
        "anomalies": anomalies,
        "recurring_payments_total": round(recurring_total, 2),
        "spending_trend": _get_spending_trend(current_expenses, last_expenses),
        "top_category_breakdown": [
            {
                "category": cat,
                "amount": round(amt, 2),
                "percentage": round(amt / total_expenses * 100, 1) if total_expenses > 0 else 0,
            }
            for cat, amt in sorted(category_spending.items(), key=lambda x: x[1], reverse=True)[:5]
        ],
    }


def _build_monthly_review(
    last_30_txns: list,
    prev_30_txns: list,
    category_spending_30d: dict,
    category_spending_prev30d: dict,
    merchant_counts_30d: dict,
    reference_date: datetime,
    current_month_name: str,
    last_month_name: str,
    currency_symbol: str,
) -> dict:
    """Build the 30-day monthly review section.
    
    Args:
        reference_date: The latest transaction date (used as "today" for relative calculations).
        current_month_name: The formatted current month name (e.g., "December 2025").
        last_month_name: The formatted last month name (e.g., "November 2025").
        currency_symbol: The currency symbol to use in formatted strings.
    """
    debits_30d = [t for t in last_30_txns if t.transaction_type == TransactionType.DEBIT]
    credits_30d = [t for t in last_30_txns if t.transaction_type == TransactionType.CREDIT]
    debits_prev30d = [t for t in prev_30_txns if t.transaction_type == TransactionType.DEBIT]

    total_spent_30d = sum(t.amount for t in debits_30d)
    total_spent_prev30d = sum(t.amount for t in debits_prev30d)
    total_income_30d = sum(t.amount for t in credits_30d)
    transaction_count_30d = len(last_30_txns)

    # Top 3 categories with comparison
    sorted_cats = sorted(category_spending_30d.items(), key=lambda x: x[1], reverse=True)[:3]
    top_categories = []
    for cat_name, amount in sorted_cats:
        pct = round(amount / total_spent_30d * 100, 1) if total_spent_30d > 0 else 0
        prev_amount = category_spending_prev30d.get(cat_name, 0)
        change_pct = None
        if prev_amount > 0:
            change_pct = round((amount - prev_amount) / prev_amount * 100, 1)
        top_categories.append({
            "name": cat_name,
            "amount": round(amount, 2),
            "percentage": pct,
            "change_vs_previous": change_pct,
        })

    # Biggest single expense and income
    biggest_expense = None
    if debits_30d:
        max_debit = max(debits_30d, key=lambda t: t.amount)
        biggest_expense = {
            "amount": round(max_debit.amount, 2),
            "description": (max_debit.description or "Unknown")[:60],
            "date": max_debit.date.isoformat() if max_debit.date else None,
        }

    biggest_income = None
    if credits_30d:
        max_credit = max(credits_30d, key=lambda t: t.amount)
        biggest_income = {
            "amount": round(max_credit.amount, 2),
            "description": (max_credit.description or "Unknown")[:60],
            "date": max_credit.date.isoformat() if max_credit.date else None,
        }

    # Unique merchants count
    unique_merchants = len(merchant_counts_30d)

    # Average transaction size
    avg_transaction = round(total_spent_30d / len(debits_30d), 2) if debits_30d else 0

    # Days with no spending
    spending_dates = set()
    for t in debits_30d:
        if t.date:
            spending_dates.add(t.date.date())
    no_spend_days = 30 - len(spending_dates)

    # Summary sentence with month name
    summary_sentence = (
        f"In {current_month_name}, you spent {currency_symbol}{total_spent_30d:,.0f} "
        f"across {len(debits_30d)} transactions"
    )

    # Comparison sentence
    comparison_sentence = None
    if total_spent_prev30d > 0:
        change = ((total_spent_30d - total_spent_prev30d) / total_spent_prev30d) * 100
        direction = "more" if change > 0 else "less"
        comparison_sentence = (
            f"You spent {abs(change):.0f}% {direction} compared to {last_month_name}"
        )

    return {
        "summary_sentence": summary_sentence,
        "comparison_sentence": comparison_sentence,
        "total_spent": round(total_spent_30d, 2),
        "total_income": round(total_income_30d, 2),
        "transaction_count": transaction_count_30d,
        "top_categories": top_categories,
        "biggest_expense": biggest_expense,
        "biggest_income": biggest_income,
        "unique_merchants": unique_merchants,
        "average_transaction": avg_transaction,
        "no_spend_days": no_spend_days,
    }


def _build_fun_statistics(
    last_30_txns: list,
    merchant_counts_30d: dict,
    merchant_totals_30d: dict,
    category_spending_30d: dict,
    current_expenses: float,
    current_income: float,
    reference_date: datetime,
    current_month_name: str,
    currency_symbol: str,
) -> list[dict]:
    """Build playful/fun statistics using the reference date for annualization."""
    debits_30d = [t for t in last_30_txns if t.transaction_type == TransactionType.DEBIT]
    stats = []

    # Food ordering frequency
    food_keywords = ["swiggy", "zomato", "food", "dining", "restaurant", "uber eats"]
    food_orders = 0
    food_total = 0.0
    for t in debits_30d:
        desc_lower = (t.description or "").lower()
        cat_lower = (t.category.name if t.category else "").lower()
        if any(kw in desc_lower or kw in cat_lower for kw in food_keywords):
            food_orders += 1
            food_total += t.amount

    if food_orders > 0:
        frequency = max(1, round(30 / food_orders))
        stats.append({
            "icon": "🍕",
            "text": f"You ordered food {food_orders} times in {current_month_name} — that's once every {frequency} days",
            "value": food_orders,
            "type": "food_frequency",
        })
        avg_food_per_day = round(food_total / 30, 0)
        stats.append({
            "icon": "🍽️",
            "text": f"You averaged {currency_symbol}{avg_food_per_day:,.0f} per day on food & dining",
            "value": avg_food_per_day,
            "type": "food_daily_avg",
        })

    # Most expensive day
    day_spending: dict[str, float] = defaultdict(float)
    for t in debits_30d:
        if t.date:
            day_key = t.date.strftime("%B %d")
            day_spending[day_key] += t.amount
    if day_spending:
        expensive_day = max(day_spending, key=day_spending.get)
        stats.append({
            "icon": "💸",
            "text": f"Your most expensive day was {expensive_day} when you spent {currency_symbol}{day_spending[expensive_day]:,.0f}",
            "value": round(day_spending[expensive_day], 2),
            "type": "expensive_day",
        })

    # People/transfers sent
    transfer_keywords = ["upi", "transfer", "sent", "neft", "imps", "p2p"]
    unique_recipients: set[str] = set()
    for t in debits_30d:
        desc_lower = (t.description or "").lower()
        if any(kw in desc_lower for kw in transfer_keywords):
            merchant = _extract_simple_merchant(t.description or "")
            if merchant:
                unique_recipients.add(merchant)
    if unique_recipients:
        stats.append({
            "icon": "👥",
            "text": f"You sent money to {len(unique_recipients)} different people/accounts in {current_month_name}",
            "value": len(unique_recipients),
            "type": "unique_recipients",
        })

    # Subscription estimation
    subscription_keywords = ["netflix", "spotify", "amazon prime", "hotstar", "youtube", "subscription", "disney", "apple"]
    sub_total = 0.0
    for t in debits_30d:
        desc_lower = (t.description or "").lower()
        if any(kw in desc_lower for kw in subscription_keywords):
            sub_total += t.amount
    if sub_total > 0:
        stats.append({
            "icon": "📺",
            "text": f"{currency_symbol}{sub_total:,.0f} of your spending was on subscriptions",
            "value": round(sub_total, 2),
            "type": "subscriptions",
        })

    # Largest single payment
    if debits_30d:
        largest = max(debits_30d, key=lambda t: t.amount)
        merchant_name = _extract_simple_merchant(largest.description or "") or "unknown"
        stats.append({
            "icon": "💰",
            "text": f"Your largest single payment was {currency_symbol}{largest.amount:,.0f} to {merchant_name}",
            "value": round(largest.amount, 2),
            "type": "largest_payment",
        })

    # Annual projection
    if current_expenses > 0:
        days_in_month = reference_date.day
        if days_in_month > 0:
            daily_rate = current_expenses / days_in_month
            annual_projection = daily_rate * 365
            stats.append({
                "icon": "📈",
                "text": f"If you keep this pace, your annual spending will be {currency_symbol}{annual_projection:,.0f}",
                "value": round(annual_projection, 2),
                "type": "annual_projection",
            })

    # Number of transactions per day average
    if debits_30d:
        txns_per_day = round(len(debits_30d) / 30, 1)
        stats.append({
            "icon": "⚡",
            "text": f"You make about {txns_per_day} transactions per day on average",
            "value": txns_per_day,
            "type": "txns_per_day",
        })

    return stats


def _build_spending_personality(
    category_spending_30d: dict,
    last_30_txns: list,
    current_income: float,
    current_expenses: float,
    savings_rate: float,
) -> dict:
    """Determine a fun spending personality label."""
    total_spent_30d = sum(category_spending_30d.values())

    if total_spent_30d == 0:
        return {"emoji": "🆕", "label": "New Tracker", "description": "Just getting started with tracking!"}

    # Calculate percentages
    food_pct = 0.0
    shopping_pct = 0.0
    housing_pct = 0.0
    investment_pct = 0.0

    food_keywords = ["food", "dining", "restaurant", "groceries", "swiggy", "zomato"]
    shopping_keywords = ["shopping", "amazon", "flipkart", "retail", "clothing"]
    housing_keywords = ["utilities", "rent", "electricity", "water", "gas", "maintenance"]
    investment_keywords = ["investment", "mutual fund", "stocks", "sip", "trading"]

    for cat, amount in category_spending_30d.items():
        cat_lower = cat.lower()
        pct = (amount / total_spent_30d) * 100
        if any(kw in cat_lower for kw in food_keywords):
            food_pct += pct
        if any(kw in cat_lower for kw in shopping_keywords):
            shopping_pct += pct
        if any(kw in cat_lower for kw in housing_keywords):
            housing_pct += pct
        if any(kw in cat_lower for kw in investment_keywords):
            investment_pct += pct

    # Determine personality (priority order)
    if savings_rate >= 20:
        return {
            "emoji": "💎",
            "label": "Saver",
            "description": f"You're saving {savings_rate:.0f}% of your income. Impressive financial discipline!",
        }
    if current_income > 0 and current_expenses / current_income > 0.9:
        return {
            "emoji": "💳",
            "label": "Spender",
            "description": "You're using most of your income. Consider building more savings buffer.",
        }
    if food_pct > 30:
        return {
            "emoji": "🍲",
            "label": "Foodie",
            "description": f"Food & dining takes up {food_pct:.0f}% of your spending. You love good food!",
        }
    if shopping_pct > 25:
        return {
            "emoji": "🛍️",
            "label": "Shopaholic",
            "description": f"Shopping is {shopping_pct:.0f}% of your budget. You know what you want!",
        }
    if housing_pct > 50:
        return {
            "emoji": "🏠",
            "label": "Homebody",
            "description": f"Housing & utilities take {housing_pct:.0f}% of spending. Home is where the heart is.",
        }
    if investment_pct > 10:
        return {
            "emoji": "📈",
            "label": "Investor",
            "description": "You're actively investing. Building wealth for the future!",
        }

    return {
        "emoji": "⚖️",
        "label": "Balanced Spender",
        "description": "Your spending is well-distributed across categories. Nicely balanced!",
    }


def _build_detailed_insights(
    last_30_txns: list,
    merchant_counts_30d: dict,
    merchant_totals_30d: dict,
    current_income: float,
    current_expenses: float,
    savings_rate: float,
    category_spending_30d: dict,
    category_spending_prev30d: dict,
    reference_date: datetime,
    current_month_name: str,
    currency_symbol: str,
) -> list[dict]:
    """Build paragraph-style detailed insights."""
    paragraphs = []
    debits_30d = [t for t in last_30_txns if t.transaction_type == TransactionType.DEBIT]

    # Food delivery insight
    food_merchants: dict[str, int] = defaultdict(int)
    food_keywords = ["swiggy", "zomato", "uber eats", "food"]
    for t in debits_30d:
        desc_lower = (t.description or "").lower()
        for kw in food_keywords:
            if kw in desc_lower:
                merchant = _extract_simple_merchant(t.description or "")
                if merchant:
                    food_merchants[merchant] += 1
                break

    if food_merchants:
        top_food = max(food_merchants, key=food_merchants.get)
        top_food_count = food_merchants[top_food]
        total_food_orders = sum(food_merchants.values())
        paragraphs.append({
            "title": "Food & Dining Habits",
            "icon": "🍽️",
            "text": (
                f"In {current_month_name}, you've been active in food ordering, with {total_food_orders} orders total. "
                f"{top_food} alone accounts for {top_food_count} of those. "
                f"Your dining habits suggest a preference for convenience and ordering in."
            ),
        })

    # Income pattern insight
    credits_30d = [t for t in last_30_txns if t.transaction_type == TransactionType.CREDIT]
    if credits_30d:
        salary_candidates = [t for t in credits_30d if t.amount == max(c.amount for c in credits_30d)]
        if salary_candidates:
            salary = salary_candidates[0]
            day = salary.date.day if salary.date else None
            if day:
                paragraphs.append({
                    "title": "Income Pattern",
                    "icon": "💰",
                    "text": (
                        f"Your largest credit of {currency_symbol}{salary.amount:,.0f} arrived on the {_ordinal(day)}. "
                        f"Consistent income timing helps with budgeting and planning."
                    ),
                })

    # Spending trend insight
    total_30d = sum(category_spending_30d.values())
    total_prev30d = sum(category_spending_prev30d.values())
    if total_prev30d > 0 and total_30d > 0:
        change_pct = ((total_30d - total_prev30d) / total_prev30d) * 100
        # Find categories with biggest changes
        improving_cats = []
        worsening_cats = []
        for cat, amount in category_spending_30d.items():
            prev = category_spending_prev30d.get(cat, 0)
            if prev > 0:
                cat_change = ((amount - prev) / prev) * 100
                if cat_change < -15:
                    improving_cats.append((cat, abs(cat_change)))
                elif cat_change > 20:
                    worsening_cats.append((cat, cat_change))

        if improving_cats or worsening_cats:
            text_parts = []
            if improving_cats:
                improving_cats.sort(key=lambda x: x[1], reverse=True)
                best = improving_cats[0]
                text_parts.append(
                    f"Great news — you've reduced spending in {best[0]} by {best[1]:.0f}%"
                )
            if worsening_cats:
                worsening_cats.sort(key=lambda x: x[1], reverse=True)
                worst = worsening_cats[0]
                text_parts.append(
                    f"spending on {worst[0]} increased by {worst[1]:.0f}%"
                )

            if change_pct < 0:
                summary_text = (
                    f"Overall, your spending decreased by {abs(change_pct):.0f}% compared to the previous period. "
                    + ". However, ".join(text_parts) + "."
                )
            else:
                summary_text = (
                    f"Your spending increased by {change_pct:.0f}% compared to the previous period. "
                    + ". ".join(text_parts) + "."
                )

            paragraphs.append({
                "title": "Spending Trends",
                "icon": "📊",
                "text": summary_text,
            })

    # Savings insight
    if current_income > 0:
        if savings_rate >= 20:
            paragraphs.append({
                "title": "Savings Health",
                "icon": "🏦",
                "text": (
                    f"With a savings rate of {savings_rate:.0f}%, you're above the recommended 20% threshold. "
                    f"You're saving {currency_symbol}{(current_income - current_expenses):,.0f} relative to income this period. "
                    f"Keep this up and you'll build a solid financial buffer."
                ),
            })
        elif savings_rate >= 0:
            paragraphs.append({
                "title": "Savings Health",
                "icon": "🏦",
                "text": (
                    f"Your savings rate is {savings_rate:.0f}%. While positive, financial experts "
                    f"recommend aiming for at least 20%. Small adjustments in discretionary spending "
                    f"could help you reach that goal."
                ),
            })
        else:
            paragraphs.append({
                "title": "Savings Alert",
                "icon": "⚠️",
                "text": (
                    f"Your expenses currently exceed your income, resulting in a negative savings rate of {savings_rate:.0f}%. "
                    f"This is unsustainable long-term. Review your largest expense categories "
                    f"for areas to cut back."
                ),
            })

    return paragraphs


def _build_achievements(
    all_txns: list,
    savings_rate: float,
    current_savings_rate: float,
    reference_date: datetime,
    current_month_name: str,
    currency_symbol: str,
) -> list[dict]:
    """Build milestones and achievements."""
    achievements = []

    # Months tracked
    if all_txns:
        earliest = min(t.date for t in all_txns if t.date)
        if earliest:
            months_tracked = max(1, (reference_date.year - earliest.year) * 12 + reference_date.month - earliest.month)
            if months_tracked >= 1:
                achievements.append({
                    "icon": "📊",
                    "title": f"Tracked {months_tracked} month{'s' if months_tracked > 1 else ''} of spending",
                    "type": "milestone",
                })

    # Transaction count milestones
    txn_count = len(all_txns)
    if txn_count >= 1000:
        achievements.append({
            "icon": "🏆",
            "title": f"{txn_count:,} transactions tracked!",
            "type": "milestone",
        })
    elif txn_count >= 500:
        achievements.append({
            "icon": "🥈",
            "title": f"{txn_count:,} transactions tracked",
            "type": "milestone",
        })
    elif txn_count >= 100:
        achievements.append({
            "icon": "🥉",
            "title": f"{txn_count:,} transactions logged",
            "type": "milestone",
        })

    # Savings milestones
    if current_savings_rate >= 30:
        achievements.append({
            "icon": "💎",
            "title": f"Savings rate above 30% in {current_month_name}!",
            "type": "positive",
        })
    elif current_savings_rate >= 20:
        achievements.append({
            "icon": "🎯",
            "title": f"Hit the 20% savings target in {current_month_name}",
            "type": "positive",
        })

    # Consistency
    if savings_rate >= 15:
        achievements.append({
            "icon": "⚡",
            "title": "Maintaining positive savings overall",
            "type": "streak",
        })

    # First time tracking
    if txn_count < 50:
        achievements.append({
            "icon": "🌱",
            "title": "Just getting started — keep tracking!",
            "type": "encouragement",
        })

    return achievements


def _build_predictions(
    current_expenses: float,
    current_income: float,
    recurring_total: float,
    savings_rate: float,
    reference_date: datetime,
    next_month_name: str,
    currency_symbol: str,
) -> dict:
    """Build predictions for next month and year-end based on reference date."""
    days_elapsed = reference_date.day
    days_in_month = 30

    # Monthly projection
    if days_elapsed > 0:
        daily_expense_rate = current_expenses / days_elapsed
        projected_monthly = daily_expense_rate * days_in_month
    else:
        projected_monthly = current_expenses

    # Annual subscription cost
    annual_subscriptions = recurring_total * 12

    # Year-end savings projection (remaining months from reference date)
    months_remaining = 12 - reference_date.month
    monthly_savings = current_income - current_expenses if current_income > current_expenses else 0
    projected_yearly_savings = monthly_savings * months_remaining

    # Annual income projection
    annual_income_projection = current_income * 12

    return {
        "next_month_expense": round(projected_monthly, 2),
        "annual_subscription_cost": round(annual_subscriptions, 2),
        "year_end_savings": round(projected_yearly_savings, 2),
        "annual_income_projection": round(annual_income_projection, 2),
        "sentences": [
            f"At your current pace, you'll spend {currency_symbol}{projected_monthly:,.0f} in {next_month_name}",
            f"Your recurring costs will total {currency_symbol}{annual_subscriptions:,.0f} for the year",
            f"You're on track to save {currency_symbol}{projected_yearly_savings:,.0f} by year-end" if monthly_savings > 0
            else "At this rate, you won't accumulate additional savings this year",
        ],
    }


# ─── Helpers ──────────────────────────────────────────────────────────────────


def _empty_summary() -> dict:
    """Return an empty summary when no data is available."""
    return {
        "overview": {
            "total_income": 0,
            "total_expenses": 0,
            "net_savings": 0,
            "savings_rate": 0,
            "current_month_income": 0,
            "current_month_expenses": 0,
            "current_month_savings_rate": 0,
            "last_month_expenses": 0,
            "expense_change_pct": None,
            "transaction_count": 0,
        },
        "habits": {
            "top_category": None,
            "top_category_amount": 0,
            "top_category_change_pct": None,
            "top_merchants": [],
            "categories_used": 0,
            "average_transaction": 0,
        },
        "insights": {
            "anomalies": [],
            "recurring_payments_total": 0,
            "spending_trend": "no_data",
            "top_category_breakdown": [],
        },
        "advice": [],
        "monthly_review": {
            "summary_sentence": "No spending data available yet",
            "comparison_sentence": None,
            "total_spent": 0,
            "total_income": 0,
            "transaction_count": 0,
            "top_categories": [],
            "biggest_expense": None,
            "biggest_income": None,
            "unique_merchants": 0,
            "average_transaction": 0,
            "no_spend_days": 30,
        },
        "fun_statistics": [],
        "spending_personality": {
            "emoji": "🆕",
            "label": "New Tracker",
            "description": "Upload a statement to discover your spending personality!",
        },
        "detailed_insights": [],
        "achievements": [],
        "predictions": {
            "next_month_expense": 0,
            "annual_subscription_cost": 0,
            "year_end_savings": 0,
            "annual_income_projection": 0,
            "sentences": [],
        },
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "period": None,
    }


def _extract_simple_merchant(description: str) -> Optional[str]:
    """Extract a simplified merchant name from transaction description."""
    import re
    text = description.upper().strip()

    for prefix in ["POS ", "UPI/", "UPI-", "NEFT/", "IMPS/", "ACH D-"]:
        if text.startswith(prefix):
            text = text[len(prefix):]

    text = re.sub(r"\d{6,}", "", text)
    text = re.sub(r"\s+", " ", text).strip()

    words = text.split()
    if not words:
        return None

    merchant = " ".join(words[:2]).strip()
    if len(merchant) < 3:
        return None

    return merchant.title()


def _estimate_recurring_total(transactions: list) -> float:
    """Estimate total recurring payments by finding repeated merchants."""
    merchant_amounts: dict[str, list[float]] = defaultdict(list)
    for t in transactions:
        if t.transaction_type == TransactionType.DEBIT and t.description:
            merchant = _extract_simple_merchant(t.description)
            if merchant:
                merchant_amounts[merchant].append(t.amount)

    recurring_total = 0.0
    for merchant, amounts in merchant_amounts.items():
        if len(amounts) >= 3:
            avg = sum(amounts) / len(amounts)
            consistent = all(abs(a - avg) / avg < 0.2 for a in amounts) if avg > 0 else False
            if consistent:
                recurring_total += avg

    return recurring_total


def _detect_anomalies(all_txns: list, category_spending: dict) -> list:
    """Detect transactions significantly above average for their category."""
    anomalies = []
    if not category_spending:
        return anomalies

    category_txn_counts: dict[str, int] = defaultdict(int)
    for t in all_txns:
        if t.transaction_type == TransactionType.DEBIT and t.category:
            category_txn_counts[t.category.name] += 1

    category_avg = {
        cat: amount / category_txn_counts[cat]
        for cat, amount in category_spending.items()
        if category_txn_counts[cat] > 2
    }

    for t in all_txns[:50]:
        if t.transaction_type == TransactionType.DEBIT and t.category:
            avg = category_avg.get(t.category.name, 0)
            if avg > 0 and t.amount > avg * 3:
                anomalies.append({
                    "description": t.description[:60] if t.description else "Unknown",
                    "amount": round(t.amount, 2),
                    "category": t.category.name,
                    "average_for_category": round(avg, 2),
                    "multiplier": round(t.amount / avg, 1),
                })
    return anomalies[:5]


def _get_spending_trend(current: float, last: float) -> str:
    """Determine spending trend direction."""
    if last == 0:
        return "no_comparison"
    change = (current - last) / last * 100
    if change > 10:
        return "increasing"
    elif change < -10:
        return "decreasing"
    return "stable"


def _generate_advice(
    savings_rate: float,
    current_expenses: float,
    current_income: float,
    last_expenses: float,
    top_category: Optional[str],
    anomalies: list,
    recurring_total: float,
) -> list[dict]:
    """Generate actionable financial advice based on data patterns."""
    advice = []

    if savings_rate < 0:
        advice.append({
            "type": "warning",
            "icon": "🚨",
            "title": "Spending exceeds income",
            "message": f"You're spending more than you earn. Your savings rate is {savings_rate}%. Consider cutting non-essential expenses.",
        })
    elif savings_rate < 10:
        advice.append({
            "type": "caution",
            "icon": "⚠️",
            "title": "Low savings rate",
            "message": f"Your savings rate is {savings_rate}%. Financial experts recommend saving at least 20% of income.",
        })
    elif savings_rate >= 30:
        advice.append({
            "type": "positive",
            "icon": "🎉",
            "title": "Great savings rate!",
            "message": f"You're saving {savings_rate}% of your income. Keep up the excellent financial discipline!",
        })

    if last_expenses > 0 and current_expenses > last_expenses * 1.2:
        increase_pct = round((current_expenses - last_expenses) / last_expenses * 100, 0)
        advice.append({
            "type": "caution",
            "icon": "📈",
            "title": "Spending increasing",
            "message": f"Your expenses are up {increase_pct}% compared to last month. Review your recent purchases.",
        })

    if top_category and current_expenses > 0:
        advice.append({
            "type": "info",
            "icon": "📊",
            "title": f"Top spending: {top_category}",
            "message": f"'{top_category}' is your biggest expense category. Consider if there are ways to optimize spending here.",
        })

    if anomalies:
        advice.append({
            "type": "info",
            "icon": "🔍",
            "title": f"{len(anomalies)} unusual transaction(s) detected",
            "message": "Some transactions are significantly above your typical spending in their category. Review them for accuracy.",
        })

    if recurring_total > 0 and current_income > 0:
        recurring_pct = recurring_total / current_income * 100
        if recurring_pct > 50:
            advice.append({
                "type": "caution",
                "icon": "🔄",
                "title": "High recurring commitments",
                "message": f"Recurring payments make up ~{round(recurring_pct)}% of your income. Consider reviewing subscriptions you no longer use.",
            })

    if not advice:
        advice.append({
            "type": "positive",
            "icon": "✅",
            "title": "Looking good!",
            "message": "Your finances appear to be in good shape. Keep monitoring regularly to stay on track.",
        })

    return advice


def _ordinal(n: int) -> str:
    """Convert integer to ordinal string (1st, 2nd, 3rd, etc.)."""
    if 11 <= (n % 100) <= 13:
        suffix = "th"
    else:
        suffix = {1: "st", 2: "nd", 3: "rd"}.get(n % 10, "th")
    return f"{n}{suffix}"


# ─── Monthly Personality Tabs + Year Recap ──────────────────────────────────


def get_available_months(db: Session, user_id: int) -> list[dict]:
    """Return the list of months that have at least one transaction.

    Args:
        db: Database session.
        user_id: The user to query.

    Returns:
        A list of dicts ordered newest-first, each shaped like
        ``{"month": "2025-03", "label": "March 2025", "transaction_count": 42}``.
    """
    txns = (
        db.query(Transaction)
        .filter(Transaction.user_id == user_id)
        .filter(Transaction.date.isnot(None))
        .all()
    )

    buckets: dict[str, int] = defaultdict(int)
    for t in txns:
        if t.date:
            buckets[t.date.strftime("%Y-%m")] += 1

    months = []
    for key in sorted(buckets.keys(), reverse=True):
        year, month = key.split("-")
        label = datetime(int(year), int(month), 1).strftime("%B %Y")
        months.append({
            "month": key,
            "label": label,
            "transaction_count": buckets[key],
        })
    return months


def _month_bounds(month: str) -> tuple[datetime, datetime]:
    """Return [start, end) datetime bounds for a 'YYYY-MM' month string."""
    year, mon = (int(p) for p in month.split("-"))
    start = datetime(year, mon, 1, tzinfo=timezone.utc)
    if mon == 12:
        end = datetime(year + 1, 1, 1, tzinfo=timezone.utc)
    else:
        end = datetime(year, mon + 1, 1, tzinfo=timezone.utc)
    return start, end


def _txn_in_range(t: Transaction, start: datetime, end: datetime) -> bool:
    """Check whether a transaction's date falls in [start, end), tz-safe."""
    if not t.date:
        return False
    d = t.date
    # Normalise naive datetimes to UTC so comparisons never raise.
    if d.tzinfo is None:
        d = d.replace(tzinfo=timezone.utc)
    return start <= d < end


def _compute_month_stats(
    month_txns: list[Transaction],
    prev_txns: list[Transaction],
) -> dict:
    """Compute the shared underlying stats for a single month.

    These raw numbers are tone-agnostic; the tone templates phrase them
    differently. Reused by all four monthly tones.
    """
    debits = [t for t in month_txns if t.transaction_type == TransactionType.DEBIT]
    credits = [t for t in month_txns if t.transaction_type == TransactionType.CREDIT]
    prev_debits = [t for t in prev_txns if t.transaction_type == TransactionType.DEBIT]

    total_spent = sum(t.amount for t in debits)
    total_income = sum(t.amount for t in credits)
    prev_spent = sum(t.amount for t in prev_debits)
    net_savings = total_income - total_spent
    savings_rate = round(net_savings / total_income * 100, 1) if total_income > 0 else 0.0

    expense_change_pct = None
    if prev_spent > 0:
        expense_change_pct = round((total_spent - prev_spent) / prev_spent * 100, 1)

    # Category breakdown
    category_spending: dict[str, float] = defaultdict(float)
    category_counts: dict[str, int] = defaultdict(int)
    for t in debits:
        if t.category:
            category_spending[t.category.name] += t.amount
            category_counts[t.category.name] += 1

    top_categories = []
    for cat, amt in sorted(category_spending.items(), key=lambda x: x[1], reverse=True)[:5]:
        pct = round(amt / total_spent * 100, 1) if total_spent > 0 else 0
        top_categories.append({
            "name": cat,
            "amount": round(amt, 2),
            "percentage": pct,
            "count": category_counts[cat],
        })

    # Merchant analysis
    merchant_counts: dict[str, int] = defaultdict(int)
    merchant_totals: dict[str, float] = defaultdict(float)
    for t in debits:
        if t.description:
            merchant = _extract_simple_merchant(t.description)
            if merchant:
                merchant_counts[merchant] += 1
                merchant_totals[merchant] += t.amount

    top_merchants = []
    for name, count in sorted(merchant_counts.items(), key=lambda x: x[1], reverse=True)[:5]:
        top_merchants.append({
            "name": name,
            "frequency": count,
            "total_spent": round(merchant_totals[name], 2),
        })

    biggest_expense = None
    if debits:
        mx = max(debits, key=lambda t: t.amount)
        biggest_expense = {
            "amount": round(mx.amount, 2),
            "description": (mx.description or "Unknown")[:60],
            "date": mx.date.isoformat() if mx.date else None,
        }

    # No-spend days
    spend_dates = {t.date.date() for t in debits if t.date}
    days_in_month = max((t.date.day for t in month_txns if t.date), default=30)
    no_spend_days = max(0, days_in_month - len(spend_dates))

    avg_txn = round(total_spent / len(debits), 2) if debits else 0

    return {
        "total_spent": round(total_spent, 2),
        "total_income": round(total_income, 2),
        "net_savings": round(net_savings, 2),
        "savings_rate": savings_rate,
        "transaction_count": len(month_txns),
        "debit_count": len(debits),
        "credit_count": len(credits),
        "expense_change_pct": expense_change_pct,
        "top_categories": top_categories,
        "top_merchants": top_merchants,
        "biggest_expense": biggest_expense,
        "no_spend_days": no_spend_days,
        "average_transaction": avg_txn,
    }


def _phrase_month_lines(stats: dict, tone: str, month_label: str,
                        prev_month_label: str, symbol: str) -> list[dict]:
    """Apply tone-specific templates to monthly stats, returning display lines."""
    lines: list[dict] = []

    def amt(v: float) -> str:
        return f"{symbol}{v:,.0f}"

    top_cats = stats["top_categories"]
    top_merchants = stats["top_merchants"]
    rate = stats["savings_rate"]

    if tone == "roast":
        lines.append({"icon": "🔥", "text": tones.roast_opener(month_label)})
        for cat in top_cats[:3]:
            lines.append({"icon": "💸", "text": tones.roast_category_line(
                cat["name"], amt(cat["amount"]), month_label)})
        if top_merchants and top_merchants[0]["frequency"] >= 3:
            m = top_merchants[0]
            lines.append({"icon": "🧾", "text": tones.roast_merchant_line(
                m["name"], m["frequency"])})
        lines.append({"icon": "📉", "text": tones.roast_savings_line(rate)})

    elif tone == "praise":
        lines.append({"icon": "🌟", "text": tones.praise_opener(month_label)})
        lines.append({"icon": "🏦", "text": tones.praise_savings_line(rate)})
        # Praise the smallest of the top categories (relative restraint).
        if top_cats:
            lean = min(top_cats, key=lambda c: c["amount"])
            lines.append({"icon": "💚", "text": tones.praise_category_line(
                lean["name"], amt(lean["amount"]), month_label)})
        if stats["no_spend_days"] > 0:
            lines.append({"icon": "🧘", "text": tones.praise_consistency_line(
                stats["no_spend_days"])})

    elif tone == "executive":
        lines.append({"icon": "•", "text": tones.exec_overview_line(
            symbol, stats["total_spent"], stats["transaction_count"], month_label)})
        for cat in top_cats[:3]:
            lines.append({"icon": "•", "text": tones.exec_category_line(
                cat["name"], symbol, cat["amount"], cat["percentage"])})
        mom = tones.exec_mom_line(symbol, stats["expense_change_pct"], prev_month_label)
        if mom:
            lines.append({"icon": "•", "text": mom})
        lines.append({"icon": "•", "text": tones.exec_savings_line(rate)})

    else:  # fun
        # Fun phrases already embed a leading emoji in their text, so the line
        # `icon` is left empty to avoid rendering a duplicate orphan emoji.
        lines.append({"icon": "", "text": tones.fun_opener(month_label)})
        if top_cats:
            big = top_cats[0]
            lines.append({"icon": "", "text": tones.fun_category_line(
                big["name"], amt(big["amount"]), month_label)})
        if top_merchants and top_merchants[0]["frequency"] >= 2:
            m = top_merchants[0]
            lines.append({"icon": "", "text": tones.fun_count_line(
                f"{m['name']} visits", m["frequency"])})
        lines.append({"icon": "", "text": tones.fun_savings_line(rate)})

    return lines


def generate_monthly_summary(db: Session, user_id: int, month: str, tone: str) -> dict:
    """Generate a tone-flavoured summary for a specific month.

    Args:
        db: Database session.
        user_id: The user to summarise.
        month: Target month in ``"YYYY-MM"`` format.
        tone: One of ``"roast"``, ``"praise"``, ``"executive"``, ``"fun"``.

    Returns:
        A dict with ``month``, ``month_label``, ``tone``, tone ``meta``, the
        raw ``stats`` block, and tone-phrased ``lines``. Amounts use the user's
        dominant currency symbol.

    Raises:
        ValueError: If ``tone`` is not a recognised tone.
    """
    if tone not in tones.VALID_TONES:
        raise ValueError(f"Invalid tone '{tone}'. Must be one of {tones.VALID_TONES}.")

    dominant_currency = get_dominant_currency(db, user_id)
    symbol = get_currency_symbol(dominant_currency)

    start, end = _month_bounds(month)
    prev_end = start
    prev_start = (start.replace(day=1) - timedelta(days=1)).replace(
        day=1, hour=0, minute=0, second=0, microsecond=0
    )

    all_txns = (
        db.query(Transaction)
        .filter(Transaction.user_id == user_id)
        .filter(Transaction.date.isnot(None))
        .all()
    )

    month_txns = [t for t in all_txns if _txn_in_range(t, start, end)]
    prev_txns = [t for t in all_txns if _txn_in_range(t, prev_start, prev_end)]

    month_label = start.strftime("%B %Y")
    prev_month_label = prev_start.strftime("%B %Y")

    stats = _compute_month_stats(month_txns, prev_txns)
    lines = _phrase_month_lines(stats, tone, month_label, prev_month_label, symbol)

    return {
        "month": month,
        "month_label": month_label,
        "tone": tone,
        "meta": tones.TONE_META[tone],
        "currency": dominant_currency,
        "currency_symbol": symbol,
        "has_data": stats["transaction_count"] > 0,
        "stats": stats,
        "lines": lines,
        "generated_at": datetime.now(timezone.utc).isoformat(),
    }


def _classify_year_personality(category_spending: dict, savings_rate: float) -> str:
    """Choose a year-recap personality key from spending signals."""
    total = sum(category_spending.values())
    if total <= 0:
        return "balanced"

    if savings_rate >= 30:
        return "saver"

    signal_keywords = {
        "coffee": ["coffee", "cafe", "starbucks", "barista"],
        "food": ["food", "dining", "restaurant", "swiggy", "zomato", "groceries"],
        "shopping": ["shopping", "amazon", "flipkart", "retail", "clothing"],
        "travel": ["travel", "flight", "hotel", "airbnb", "trip"],
        "entertainment": ["entertainment", "movie", "concert", "netflix", "spotify", "game"],
        "housing": ["rent", "housing", "utilities", "electricity", "maintenance"],
        "transport": ["transport", "fuel", "uber", "ola", "metro", "cab"],
        "investment": ["investment", "mutual fund", "stocks", "sip", "trading"],
    }

    signal_totals: dict[str, float] = defaultdict(float)
    for cat, amount in category_spending.items():
        cat_lower = cat.lower()
        for signal, kws in signal_keywords.items():
            if any(kw in cat_lower for kw in kws):
                signal_totals[signal] += amount

    if not signal_totals:
        return "balanced"

    dominant = max(signal_totals, key=signal_totals.get)
    # Only assign a themed title if the signal is meaningfully dominant.
    if signal_totals[dominant] / total >= 0.20:
        return dominant
    return "balanced"


def generate_yearly_recap(db: Session, user_id: int, year: int) -> dict:
    """Generate a Spotify-Wrapped-style recap for a full calendar year.

    Args:
        db: Database session.
        user_id: The user to summarise.
        year: The calendar year (e.g. ``2025``).

    Returns:
        A dict with ``personality_title``, ``headline_stats``, ``top_categories``,
        ``top_merchants``, ``biggest_transactions``, ``surprising_stats``,
        ``achievements``, and a closing ``narrative``. Amounts use the user's
        dominant currency symbol.
    """
    dominant_currency = get_dominant_currency(db, user_id)
    symbol = get_currency_symbol(dominant_currency)

    start = datetime(year, 1, 1, tzinfo=timezone.utc)
    end = datetime(year + 1, 1, 1, tzinfo=timezone.utc)

    all_txns = (
        db.query(Transaction)
        .filter(Transaction.user_id == user_id)
        .filter(Transaction.date.isnot(None))
        .all()
    )
    year_txns = [t for t in all_txns if _txn_in_range(t, start, end)]

    debits = [t for t in year_txns if t.transaction_type == TransactionType.DEBIT]
    credits = [t for t in year_txns if t.transaction_type == TransactionType.CREDIT]

    total_spent = sum(t.amount for t in debits)
    total_income = sum(t.amount for t in credits)
    net_savings = total_income - total_spent

    if not year_txns:
        return {
            "year": year,
            "has_data": False,
            "personality_title": "The Blank Slate",
            "personality_emoji": "🆕",
            "currency": dominant_currency,
            "currency_symbol": symbol,
            "headline_stats": {
                "total_spent": 0, "total_income": 0, "net_savings": 0,
                "transaction_count": 0, "biggest_month": None, "smallest_month": None,
                "savings_rate": 0,
            },
            "top_categories": [],
            "top_merchants": [],
            "biggest_transactions": [],
            "surprising_stats": [],
            "achievements": [],
            "narrative": f"No transactions recorded for {year} yet. Upload a statement to unlock your recap!",
            "generated_at": datetime.now(timezone.utc).isoformat(),
        }

    # Monthly spend buckets
    month_spend: dict[int, float] = defaultdict(float)
    for t in debits:
        if t.date:
            month_spend[t.date.month] += t.amount

    biggest_month = smallest_month = None
    if month_spend:
        bm = max(month_spend, key=month_spend.get)
        sm = min(month_spend, key=month_spend.get)
        biggest_month = datetime(year, bm, 1).strftime("%B")
        smallest_month = datetime(year, sm, 1).strftime("%B")

    savings_rate = round(net_savings / total_income * 100, 1) if total_income > 0 else 0.0

    # Categories
    category_spending: dict[str, float] = defaultdict(float)
    category_counts: dict[str, int] = defaultdict(int)
    for t in debits:
        if t.category:
            category_spending[t.category.name] += t.amount
            category_counts[t.category.name] += 1

    top_categories = []
    for cat, amt_v in sorted(category_spending.items(), key=lambda x: x[1], reverse=True)[:5]:
        pct = round(amt_v / total_spent * 100, 1) if total_spent > 0 else 0
        top_categories.append({
            "name": cat,
            "amount": round(amt_v, 2),
            "percentage": pct,
            "count": category_counts[cat],
        })

    # Merchants
    merchant_counts: dict[str, int] = defaultdict(int)
    merchant_totals: dict[str, float] = defaultdict(float)
    for t in debits:
        if t.description:
            merchant = _extract_simple_merchant(t.description)
            if merchant:
                merchant_counts[merchant] += 1
                merchant_totals[merchant] += t.amount

    top_merchants = []
    for name, count in sorted(merchant_counts.items(), key=lambda x: x[1], reverse=True)[:5]:
        top_merchants.append({
            "name": name,
            "frequency": count,
            "total_spent": round(merchant_totals[name], 2),
        })

    # Biggest transactions
    biggest_transactions = []
    for t in sorted(debits, key=lambda t: t.amount, reverse=True)[:5]:
        biggest_transactions.append({
            "amount": round(t.amount, 2),
            "description": (t.description or "Unknown")[:60],
            "date": t.date.isoformat() if t.date else None,
            "category": t.category.name if t.category else "Uncategorized",
        })

    # Personality
    pkey = _classify_year_personality(category_spending, savings_rate)
    personality = tones.YEAR_PERSONALITY_TITLES[pkey]
    top_category_name = top_categories[0]["name"] if top_categories else None

    # Surprising stats
    surprising_stats = _build_year_surprising_stats(
        debits, merchant_counts, day_spend_symbol=symbol, year=year,
    )

    # Achievements
    achievements = _build_year_achievements(
        len(year_txns), savings_rate, net_savings, symbol, month_spend,
    )

    return {
        "year": year,
        "has_data": True,
        "personality_title": personality["title"],
        "personality_emoji": personality["emoji"],
        "currency": dominant_currency,
        "currency_symbol": symbol,
        "headline_stats": {
            "total_spent": round(total_spent, 2),
            "total_income": round(total_income, 2),
            "net_savings": round(net_savings, 2),
            "savings_rate": savings_rate,
            "transaction_count": len(year_txns),
            "biggest_month": biggest_month,
            "smallest_month": smallest_month,
        },
        "top_categories": top_categories,
        "top_merchants": top_merchants,
        "biggest_transactions": biggest_transactions,
        "surprising_stats": surprising_stats,
        "achievements": achievements,
        "narrative": tones.year_narrative(year, personality["title"], top_category_name),
        "generated_at": datetime.now(timezone.utc).isoformat(),
    }


def _build_year_surprising_stats(
    debits: list, merchant_counts: dict, day_spend_symbol: str, year: int,
) -> list[str]:
    """Build a list of 'did you know'-style surprising stats for the year recap."""
    stats: list[str] = []
    symbol = day_spend_symbol

    # Most-visited merchant
    if merchant_counts:
        top_merchant = max(merchant_counts, key=merchant_counts.get)
        count = merchant_counts[top_merchant]
        if count >= 3:
            stats.append(f"You visited {top_merchant} {count} times this year.")

    # Biggest spending day
    day_spend: dict[str, float] = defaultdict(float)
    for t in debits:
        if t.date:
            day_key = f"{t.date.strftime('%B')} {t.date.day}"
            day_spend[day_key] += t.amount
    if day_spend:
        big_day = max(day_spend, key=day_spend.get)
        stats.append(
            f"Your biggest spending day was {big_day}, when you spent "
            f"{symbol}{day_spend[big_day]:,.0f}."
        )

    # Total transactions framing
    if debits:
        stats.append(f"You made {len(debits)} purchases across {year}.")

    # Busiest weekday
    weekday_counts: dict[int, int] = defaultdict(int)
    for t in debits:
        if t.date:
            weekday_counts[t.date.weekday()] += 1
    if weekday_counts:
        busiest = max(weekday_counts, key=weekday_counts.get)
        weekday_name = ["Monday", "Tuesday", "Wednesday", "Thursday",
                        "Friday", "Saturday", "Sunday"][busiest]
        stats.append(f"{weekday_name} was your favourite day to spend money.")

    # Average per transaction
    if debits:
        avg = sum(t.amount for t in debits) / len(debits)
        stats.append(f"Your average purchase was {symbol}{avg:,.0f}.")

    return stats


def _build_year_achievements(
    txn_count: int, savings_rate: float, net_savings: float,
    symbol: str, month_spend: dict,
) -> list[dict]:
    """Build achievement badges for the year recap."""
    achievements: list[dict] = []

    if savings_rate >= 30:
        achievements.append({"icon": "💎", "title": "Diamond Saver",
                             "description": f"Saved {savings_rate:.0f}% of income this year."})
    elif savings_rate >= 20:
        achievements.append({"icon": "🎯", "title": "Goal Crusher",
                             "description": f"Beat the 20% savings benchmark at {savings_rate:.0f}%."})
    elif savings_rate >= 0:
        achievements.append({"icon": "🌱", "title": "In the Green",
                             "description": "Stayed net-positive across the year."})

    if net_savings > 0:
        achievements.append({"icon": "🏦", "title": "Net Saver",
                             "description": f"Banked {symbol}{net_savings:,.0f} overall."})

    if txn_count >= 1000:
        achievements.append({"icon": "🏆", "title": "Power Tracker",
                             "description": f"{txn_count:,} transactions logged."})
    elif txn_count >= 500:
        achievements.append({"icon": "🥈", "title": "Dedicated Tracker",
                             "description": f"{txn_count:,} transactions logged."})

    if len(month_spend) >= 12:
        achievements.append({"icon": "📅", "title": "Full Year Streak",
                             "description": "Activity recorded in all 12 months."})

    return achievements
