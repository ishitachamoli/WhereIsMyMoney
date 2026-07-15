"""Service layer for computing financial insights from transaction data."""
from sqlalchemy.orm import Session
from sqlalchemy import func, and_
from datetime import datetime, timedelta, timezone
from typing import Optional
from collections import defaultdict
import re
import statistics

from app.models.transaction import Transaction, TransactionType
from app.models.category import Category
from app.schemas.insights import (
    RecurringTransaction,
    TopMerchant,
    TopMerchantsResponse,
    VelocityEntry,
    VelocityResponse,
    OutlierTransaction,
    DayPattern,
    DayPatternsResponse,
    PaymentMethodEntry,
    PaymentMethodsResponse,
    InsightsSummary,
    Subscription,
    SubscriptionsResponse,
)


def _extract_merchant_key(description: str) -> str:
    """
    Extract a normalized merchant key from a transaction description.
    Handles UPI, NEFT, IMPS, POS patterns common in Indian banking.
    """
    desc = description.strip()

    upi_match = re.search(
        r'(?:UPI|upi)[/-](?:DR|CR|dr|cr)[/-]\d+[/-]([^/]+)', desc
    )
    if upi_match:
        return upi_match.group(1).strip().upper()

    neft_match = re.search(r'NEFT[*\-/][A-Z0-9]+[*\-/][^*\-/]+[*\-/](.+)', desc)
    if neft_match:
        return neft_match.group(1).strip().upper()[:40]

    pos_match = re.search(r'(?:POS|SBIPOS)\d*\s*(.+)', desc, re.IGNORECASE)
    if pos_match:
        return pos_match.group(1).strip().upper()[:40]

    imps_match = re.search(r'IMPS[/-]\d+[/-](.+)', desc, re.IGNORECASE)
    if imps_match:
        return imps_match.group(1).strip().upper()[:40]

    cleaned = re.sub(r'\d{6,}', '', desc)
    cleaned = re.sub(r'[/-]+', ' ', cleaned)
    cleaned = ' '.join(cleaned.split())
    return cleaned.upper()[:50] if cleaned else desc.upper()[:50]


def _detect_payment_method(description: str) -> str:
    """Detect payment method from transaction description."""
    desc = description.upper()
    if 'UPI' in desc:
        return 'UPI'
    if 'NEFT' in desc:
        return 'NEFT'
    if 'IMPS' in desc:
        return 'IMPS'
    if 'POS' in desc or 'DEBIT CARD' in desc or 'SBIPOS' in desc:
        return 'POS'
    if 'RTGS' in desc:
        return 'RTGS'
    if 'ATM' in desc or 'CASH' in desc:
        return 'ATM'
    if 'CHEQUE' in desc or 'CHQ' in desc:
        return 'Cheque'
    if 'NACH' in desc or 'ECS' in desc or 'STANDING' in desc:
        return 'Auto-Debit'
    return 'Other'


def get_recurring_transactions(
    db: Session,
    user_id: int,
    start_date: Optional[datetime] = None,
    end_date: Optional[datetime] = None,
) -> list[RecurringTransaction]:
    """Detect recurring transactions (same merchant, similar amount, regular interval)."""
    query = db.query(Transaction).filter(
        and_(
            Transaction.user_id == user_id,
            Transaction.transaction_type == TransactionType.DEBIT,
        )
    )
    if start_date:
        query = query.filter(Transaction.date >= start_date)
    if end_date:
        query = query.filter(Transaction.date <= end_date)

    transactions = query.order_by(Transaction.date).all()
    if not transactions:
        return []

    merchant_groups: dict[str, list] = defaultdict(list)
    for txn in transactions:
        key = _extract_merchant_key(txn.description)
        merchant_groups[key].append(txn)

    recurring = []
    for merchant, txns in merchant_groups.items():
        if len(txns) < 3:
            continue

        amounts = [t.amount for t in txns]
        median_amount = statistics.median(amounts)
        if median_amount == 0:
            continue

        consistent_txns = [
            t for t in txns
            if abs(t.amount - median_amount) / median_amount <= 0.10
        ]

        if len(consistent_txns) < 3:
            continue

        dates = sorted([t.date for t in consistent_txns])
        intervals = [
            (dates[i + 1] - dates[i]).days for i in range(len(dates) - 1)
        ]

        if not intervals:
            continue

        avg_interval = statistics.mean(intervals)

        if 25 <= avg_interval <= 35:
            frequency = "monthly"
        elif 5 <= avg_interval <= 9:
            frequency = "weekly"
        elif 80 <= avg_interval <= 100:
            frequency = "quarterly"
        else:
            continue

        last_date = dates[-1]
        next_expected = last_date + timedelta(days=int(avg_interval))

        recurring.append(RecurringTransaction(
            merchant=merchant[:50],
            average_amount=round(statistics.mean(amounts), 2),
            frequency=frequency,
            occurrence_count=len(consistent_txns),
            last_date=last_date.strftime("%Y-%m-%d"),
            next_expected_date=next_expected.strftime("%Y-%m-%d"),
            total_spent=round(sum(amounts), 2),
        ))

    recurring.sort(key=lambda r: r.total_spent, reverse=True)
    return recurring


def get_top_merchants(
    db: Session,
    user_id: int,
    start_date: Optional[datetime] = None,
    end_date: Optional[datetime] = None,
    limit: int = 10,
) -> TopMerchantsResponse:
    """Group transactions by merchant, rank by frequency and total spend."""
    query = db.query(Transaction).filter(
        and_(
            Transaction.user_id == user_id,
            Transaction.transaction_type == TransactionType.DEBIT,
        )
    )
    if start_date:
        query = query.filter(Transaction.date >= start_date)
    if end_date:
        query = query.filter(Transaction.date <= end_date)

    transactions = query.all()
    if not transactions:
        return TopMerchantsResponse(by_frequency=[], by_total_spend=[])

    total_spending = sum(t.amount for t in transactions)
    merchant_stats: dict[str, dict] = defaultdict(
        lambda: {"count": 0, "total": 0.0}
    )

    for txn in transactions:
        key = _extract_merchant_key(txn.description)
        merchant_stats[key]["count"] += 1
        merchant_stats[key]["total"] += txn.amount

    def build_merchant(merchant: str, stats: dict) -> TopMerchant:
        return TopMerchant(
            merchant=merchant[:50],
            transaction_count=stats["count"],
            total_amount=round(stats["total"], 2),
            average_amount=round(stats["total"] / stats["count"], 2),
            percentage_of_total=round(
                (stats["total"] / total_spending * 100) if total_spending > 0 else 0, 2
            ),
        )

    by_frequency = sorted(
        merchant_stats.items(), key=lambda x: x[1]["count"], reverse=True
    )[:limit]
    by_spend = sorted(
        merchant_stats.items(), key=lambda x: x[1]["total"], reverse=True
    )[:limit]

    return TopMerchantsResponse(
        by_frequency=[build_merchant(m, s) for m, s in by_frequency],
        by_total_spend=[build_merchant(m, s) for m, s in by_spend],
    )


def get_spending_velocity(
    db: Session,
    user_id: int,
    start_date: Optional[datetime] = None,
    end_date: Optional[datetime] = None,
) -> VelocityResponse:
    """Calculate how fast money is spent after each salary/credit."""
    query = db.query(Transaction).filter(Transaction.user_id == user_id)
    if start_date:
        query = query.filter(Transaction.date >= start_date)
    if end_date:
        query = query.filter(Transaction.date <= end_date)

    all_txns = query.order_by(Transaction.date).all()
    if not all_txns:
        return VelocityResponse(
            entries=[], average_days_to_50_percent=None,
            average_velocity_7d=0, overall_risk_level="low",
        )

    debits = [t for t in all_txns if t.transaction_type == TransactionType.DEBIT]
    credits = [t for t in all_txns if t.transaction_type == TransactionType.CREDIT]

    if not credits or not debits:
        return VelocityResponse(
            entries=[], average_days_to_50_percent=None,
            average_velocity_7d=0, overall_risk_level="low",
        )

    avg_credit = statistics.mean([c.amount for c in credits])
    large_credits = [c for c in credits if c.amount >= avg_credit * 1.5]

    if not large_credits:
        large_credits = sorted(credits, key=lambda c: c.amount, reverse=True)[:5]

    entries = []
    for credit in large_credits:
        income_date = credit.date
        income_amount = credit.amount

        week_debits = [
            d for d in debits
            if income_date <= d.date <= income_date + timedelta(days=7)
        ]
        spent_7d = sum(d.amount for d in week_debits)
        velocity_7d = (spent_7d / income_amount * 100) if income_amount > 0 else 0

        days_to_50 = None
        running_spent = 0.0
        for d in debits:
            if d.date < income_date:
                continue
            running_spent += d.amount
            if running_spent >= income_amount * 0.5:
                days_to_50 = (d.date - income_date).days
                break

        daily_burn = spent_7d / 7 if spent_7d > 0 else 0

        if velocity_7d > 50:
            risk = "high"
        elif velocity_7d > 30:
            risk = "medium"
        else:
            risk = "low"

        entries.append(VelocityEntry(
            income_date=income_date.strftime("%Y-%m-%d"),
            income_amount=round(income_amount, 2),
            spent_7_days=round(spent_7d, 2),
            velocity_7d_percent=round(velocity_7d, 1),
            days_to_50_percent=days_to_50,
            daily_burn_rate=round(daily_burn, 2),
            risk_level=risk,
        ))

    entries.sort(key=lambda e: e.income_date, reverse=True)
    entries = entries[:12]

    velocities = [e.velocity_7d_percent for e in entries]
    avg_velocity = statistics.mean(velocities) if velocities else 0

    days_list = [e.days_to_50_percent for e in entries if e.days_to_50_percent is not None]
    avg_days = statistics.mean(days_list) if days_list else None

    if avg_velocity > 50:
        overall_risk = "high"
    elif avg_velocity > 30:
        overall_risk = "medium"
    else:
        overall_risk = "low"

    return VelocityResponse(
        entries=entries,
        average_days_to_50_percent=round(avg_days, 1) if avg_days else None,
        average_velocity_7d=round(avg_velocity, 1),
        overall_risk_level=overall_risk,
    )


def get_outlier_transactions(
    db: Session,
    user_id: int,
    start_date: Optional[datetime] = None,
    end_date: Optional[datetime] = None,
    threshold_multiplier: float = 2.0,
) -> list[OutlierTransaction]:
    """Find transactions > threshold_multiplier times the average amount."""
    query = db.query(Transaction).filter(
        and_(
            Transaction.user_id == user_id,
            Transaction.transaction_type == TransactionType.DEBIT,
        )
    )
    if start_date:
        query = query.filter(Transaction.date >= start_date)
    if end_date:
        query = query.filter(Transaction.date <= end_date)

    transactions = query.all()
    if not transactions:
        return []

    amounts = [t.amount for t in transactions]
    avg_amount = statistics.mean(amounts)

    if avg_amount == 0:
        return []

    merchant_counts: dict[str, int] = defaultdict(int)
    for t in transactions:
        merchant_counts[_extract_merchant_key(t.description)] += 1

    outliers = []
    for txn in transactions:
        times_above = txn.amount / avg_amount
        if times_above >= threshold_multiplier:
            merchant_key = _extract_merchant_key(txn.description)
            is_recurring = merchant_counts[merchant_key] >= 3

            category_name = None
            if txn.category_id:
                cat = db.query(Category).filter(Category.id == txn.category_id).first()
                if cat:
                    category_name = cat.name

            outliers.append(OutlierTransaction(
                transaction_id=txn.id,
                date=txn.date.strftime("%Y-%m-%d"),
                description=txn.description[:100],
                amount=round(txn.amount, 2),
                transaction_type=txn.transaction_type.value,
                times_above_average=round(times_above, 1),
                is_recurring=is_recurring,
                category=category_name,
            ))

    outliers.sort(key=lambda o: o.amount, reverse=True)
    return outliers[:20]


def get_day_of_month_patterns(
    db: Session,
    user_id: int,
    start_date: Optional[datetime] = None,
    end_date: Optional[datetime] = None,
) -> DayPatternsResponse:
    """Aggregate spending by day of month (1-31)."""
    query = db.query(Transaction).filter(
        and_(
            Transaction.user_id == user_id,
            Transaction.transaction_type == TransactionType.DEBIT,
        )
    )
    if start_date:
        query = query.filter(Transaction.date >= start_date)
    if end_date:
        query = query.filter(Transaction.date <= end_date)

    transactions = query.all()
    if not transactions:
        return DayPatternsResponse(
            patterns=[], peak_day=1, peak_amount=0,
            lowest_day=1, lowest_amount=0,
        )

    day_stats: dict[int, dict] = {
        d: {"count": 0, "total": 0.0} for d in range(1, 32)
    }

    for txn in transactions:
        day = txn.date.day
        day_stats[day]["count"] += 1
        day_stats[day]["total"] += txn.amount

    patterns = []
    for day in range(1, 32):
        stats = day_stats[day]
        avg = stats["total"] / stats["count"] if stats["count"] > 0 else 0
        patterns.append(DayPattern(
            day=day,
            transaction_count=stats["count"],
            total_amount=round(stats["total"], 2),
            average_amount=round(avg, 2),
        ))

    active_patterns = [p for p in patterns if p.transaction_count > 0]
    if not active_patterns:
        return DayPatternsResponse(
            patterns=patterns, peak_day=1, peak_amount=0,
            lowest_day=1, lowest_amount=0,
        )

    peak = max(active_patterns, key=lambda p: p.total_amount)
    lowest = min(active_patterns, key=lambda p: p.total_amount)

    return DayPatternsResponse(
        patterns=patterns,
        peak_day=peak.day,
        peak_amount=round(peak.total_amount, 2),
        lowest_day=lowest.day,
        lowest_amount=round(lowest.total_amount, 2),
    )


def get_payment_method_breakdown(
    db: Session,
    user_id: int,
    start_date: Optional[datetime] = None,
    end_date: Optional[datetime] = None,
) -> PaymentMethodsResponse:
    """Parse transaction descriptions for payment method keywords."""
    query = db.query(Transaction).filter(Transaction.user_id == user_id)
    if start_date:
        query = query.filter(Transaction.date >= start_date)
    if end_date:
        query = query.filter(Transaction.date <= end_date)

    transactions = query.all()
    if not transactions:
        return PaymentMethodsResponse(
            methods=[], digital_percentage=0, most_used_method="N/A",
        )

    method_stats: dict[str, dict] = defaultdict(
        lambda: {"count": 0, "total": 0.0}
    )

    for txn in transactions:
        method = _detect_payment_method(txn.description)
        method_stats[method]["count"] += 1
        method_stats[method]["total"] += txn.amount

    total_count = sum(s["count"] for s in method_stats.values())
    total_amount = sum(s["total"] for s in method_stats.values())

    methods = []
    for method, stats in sorted(
        method_stats.items(), key=lambda x: x[1]["count"], reverse=True
    ):
        methods.append(PaymentMethodEntry(
            method=method,
            transaction_count=stats["count"],
            total_amount=round(stats["total"], 2),
            percentage_by_count=round(
                (stats["count"] / total_count * 100) if total_count > 0 else 0, 1
            ),
            percentage_by_amount=round(
                (stats["total"] / total_amount * 100) if total_amount > 0 else 0, 1
            ),
        ))

    digital_methods = {"UPI", "NEFT", "IMPS", "RTGS", "Auto-Debit"}
    digital_count = sum(
        s["count"] for m, s in method_stats.items() if m in digital_methods
    )
    digital_pct = (digital_count / total_count * 100) if total_count > 0 else 0

    most_used = methods[0].method if methods else "N/A"

    return PaymentMethodsResponse(
        methods=methods,
        digital_percentage=round(digital_pct, 1),
        most_used_method=most_used,
    )


def get_insights_summary(
    db: Session,
    user_id: int,
    start_date: Optional[datetime] = None,
    end_date: Optional[datetime] = None,
) -> InsightsSummary:
    """Combined overview: top 3 from each insight category."""
    recurring = get_recurring_transactions(db, user_id, start_date, end_date)
    merchants = get_top_merchants(db, user_id, start_date, end_date, limit=3)
    velocity = get_spending_velocity(db, user_id, start_date, end_date)
    outliers = get_outlier_transactions(db, user_id, start_date, end_date)
    patterns = get_day_of_month_patterns(db, user_id, start_date, end_date)
    payment_methods = get_payment_method_breakdown(db, user_id, start_date, end_date)

    return InsightsSummary(
        top_recurring=recurring[:3],
        top_merchants=merchants.by_total_spend[:3],
        velocity_risk=velocity.overall_risk_level,
        average_velocity_7d=velocity.average_velocity_7d,
        outlier_count=len(outliers),
        top_outliers=outliers[:3],
        peak_spending_day=patterns.peak_day,
        primary_payment_method=payment_methods.most_used_method,
        digital_percentage=payment_methods.digital_percentage,
    )


def get_subscriptions(
    db: Session,
    user_id: int,
    start_date: Optional[datetime] = None,
    end_date: Optional[datetime] = None,
) -> SubscriptionsResponse:
    """
    Detect subscription-like recurring debits.

    Focuses on monthly DEBIT transactions with ±10% amount consistency.
    Classifies each as 'active' (last payment within 45 days) or
    'possibly_cancelled' (no payment in 45+ days).
    """
    query = db.query(Transaction).filter(
        and_(
            Transaction.user_id == user_id,
            Transaction.transaction_type == TransactionType.DEBIT,
        )
    )
    if start_date:
        query = query.filter(Transaction.date >= start_date)
    if end_date:
        query = query.filter(Transaction.date <= end_date)

    transactions = query.order_by(Transaction.date).all()
    if not transactions:
        return SubscriptionsResponse(
            subscriptions=[],
            total_monthly_cost=0,
            total_annual_cost=0,
            active_count=0,
            possibly_cancelled_count=0,
            potential_annual_savings=0,
        )

    merchant_groups: dict[str, list] = defaultdict(list)
    for txn in transactions:
        key = _extract_merchant_key(txn.description)
        merchant_groups[key].append(txn)

    now = datetime.now(timezone.utc)
    subscriptions: list[Subscription] = []

    for merchant, txns in merchant_groups.items():
        if len(txns) < 3:
            continue

        amounts = [t.amount for t in txns]
        median_amount = statistics.median(amounts)
        if median_amount == 0:
            continue

        consistent_txns = [
            t for t in txns
            if abs(t.amount - median_amount) / median_amount <= 0.10
        ]

        if len(consistent_txns) < 3:
            continue

        dates = sorted([t.date for t in consistent_txns])
        intervals = [
            (dates[i + 1] - dates[i]).days for i in range(len(dates) - 1)
        ]

        if not intervals:
            continue

        avg_interval = statistics.mean(intervals)

        # Only monthly subscriptions (25-35 day interval)
        if not (25 <= avg_interval <= 35):
            continue

        monthly_amount = round(statistics.mean(amounts), 2)
        annual_cost = round(monthly_amount * 12, 2)

        last_date = dates[-1]
        next_expected = last_date + timedelta(days=int(avg_interval))

        # Normalize last_date to timezone-aware datetime for subtraction with now
        if isinstance(last_date, str):
            # Parse string and assume UTC
            last_date_normalized = datetime.strptime(last_date, '%Y-%m-%d').replace(tzinfo=timezone.utc)
        elif hasattr(last_date, 'tzinfo') and last_date.tzinfo is not None:
            # Already timezone-aware, use as-is (convert to UTC if needed)
            last_date_normalized = last_date.astimezone(timezone.utc)
        elif hasattr(last_date, 'year') and not hasattr(last_date, 'hour'):
            # It's a date object, convert to datetime and add UTC timezone
            last_date_normalized = datetime(last_date.year, last_date.month, last_date.day, tzinfo=timezone.utc)
        else:
            # Assume naive datetime is in UTC
            last_date_normalized = last_date.replace(tzinfo=timezone.utc)

        days_since_last = (now - last_date_normalized).days
        status = "active" if days_since_last <= 45 else "possibly_cancelled"

        subscriptions.append(Subscription(
            merchant=merchant[:50],
            monthly_amount=monthly_amount,
            annual_cost=annual_cost,
            frequency="monthly",
            occurrence_count=len(consistent_txns),
            last_date=last_date.strftime("%Y-%m-%d"),
            next_expected_date=next_expected.strftime("%Y-%m-%d"),
            status=status,
        ))

    subscriptions.sort(key=lambda s: s.annual_cost, reverse=True)

    active = [s for s in subscriptions if s.status == "active"]
    possibly_cancelled = [s for s in subscriptions if s.status == "possibly_cancelled"]

    total_monthly = round(sum(s.monthly_amount for s in active), 2)
    total_annual = round(sum(s.annual_cost for s in active), 2)
    potential_savings = round(sum(s.annual_cost for s in possibly_cancelled), 2)

    return SubscriptionsResponse(
        subscriptions=subscriptions,
        total_monthly_cost=total_monthly,
        total_annual_cost=total_annual,
        active_count=len(active),
        possibly_cancelled_count=len(possibly_cancelled),
        potential_annual_savings=potential_savings,
    )
