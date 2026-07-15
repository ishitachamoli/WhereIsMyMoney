"""Service layer for transaction operations."""
from sqlalchemy.orm import Session
from sqlalchemy import and_, or_, func, case
from typing import Optional
from datetime import datetime

from app.models.transaction import Transaction, TransactionType
from app.models.category import Category
from app.schemas.transaction import TransactionCreate, TransactionUpdate


_PAYMENT_METHOD_KEYWORDS = {
    "UPI": ["UPI", "upi"],
    "NEFT": ["NEFT", "neft"],
    "IMPS": ["IMPS", "imps"],
    "POS": ["POS", "pos"],
    "RTGS": ["RTGS", "rtgs"],
    "ATM": ["ATM", "atm"],
    "Auto-Debit": ["AUTO", "auto debit", "SI-"],
    "Cheque": ["CHQ", "cheque", "CHEQUE"],
}


def _apply_transaction_filters(
    query,
    *,
    category_id: Optional[int] = None,
    transaction_type: Optional[str] = None,
    start_date: Optional[datetime] = None,
    end_date: Optional[datetime] = None,
    search: Optional[str] = None,
    category_name: Optional[str] = None,
    needs_review: Optional[bool] = None,
    payment_method: Optional[str] = None,
):
    """Apply the shared transaction filters to a query.

    Used by both the paginated list query and the aggregate totals query so
    that the totals always reflect the exact same filtered set as ``total``.
    """
    if category_id is not None:
        query = query.filter(Transaction.category_id == category_id)
    if category_name:
        if category_name.lower() == "uncategorized":
            query = query.filter(Transaction.category_id.is_(None))
        else:
            query = query.join(Category, Transaction.category_id == Category.id).filter(
                Category.name.ilike(f"%{category_name}%")
            )
    if transaction_type:
        query = query.filter(Transaction.transaction_type == transaction_type)
    if start_date:
        query = query.filter(Transaction.date >= start_date)
    if end_date:
        query = query.filter(Transaction.date <= end_date)
    if search:
        query = query.filter(Transaction.description.ilike(f"%{search}%"))
    if needs_review:
        query = query.filter(Transaction.confidence_score < 0.7)
    if payment_method:
        keywords = _PAYMENT_METHOD_KEYWORDS.get(payment_method, [payment_method])
        conditions = [Transaction.description.ilike(f"%{kw}%") for kw in keywords]
        query = query.filter(or_(*conditions))
    return query


def get_transaction_totals(
    db: Session,
    user_id: int,
    category_id: Optional[int] = None,
    transaction_type: Optional[str] = None,
    start_date: Optional[datetime] = None,
    end_date: Optional[datetime] = None,
    search: Optional[str] = None,
    category_name: Optional[str] = None,
    needs_review: Optional[bool] = None,
    payment_method: Optional[str] = None,
) -> dict:
    """Aggregate credit/debit/net amounts for the filtered transaction set.

    Uses a single SQL aggregation (``func.sum`` + ``CASE WHEN``) over the
    entire filtered query, ignoring pagination. All amounts are returned as
    positive numbers; ``net_amount`` is ``credit_amount - debit_amount``.

    Returns:
        Dict with keys ``credit_amount``, ``debit_amount``, ``net_amount``.
        On an empty result set all values are ``0.0``.
    """
    credit_sum = func.coalesce(
        func.sum(
            case((Transaction.transaction_type == TransactionType.CREDIT, Transaction.amount), else_=0.0)
        ),
        0.0,
    )
    debit_sum = func.coalesce(
        func.sum(
            case((Transaction.transaction_type == TransactionType.DEBIT, Transaction.amount), else_=0.0)
        ),
        0.0,
    )

    query = db.query(credit_sum.label("credit"), debit_sum.label("debit")).filter(
        Transaction.user_id == user_id
    )
    query = _apply_transaction_filters(
        query,
        category_id=category_id,
        transaction_type=transaction_type,
        start_date=start_date,
        end_date=end_date,
        search=search,
        category_name=category_name,
        needs_review=needs_review,
        payment_method=payment_method,
    )

    row = query.one()
    credit_amount = float(row.credit or 0.0)
    debit_amount = float(row.debit or 0.0)
    return {
        "credit_amount": credit_amount,
        "debit_amount": debit_amount,
        "net_amount": credit_amount - debit_amount,
    }


def get_transactions(
    db: Session,
    user_id: int,
    page: int = 1,
    page_size: int = 50,
    category_id: Optional[int] = None,
    transaction_type: Optional[str] = None,
    start_date: Optional[datetime] = None,
    end_date: Optional[datetime] = None,
    search: Optional[str] = None,
    category_name: Optional[str] = None,
    sort_by: Optional[str] = None,
    sort_order: Optional[str] = None,
    needs_review: Optional[bool] = None,
    payment_method: Optional[str] = None,
) -> tuple[list[Transaction], int]:
    """Get paginated transactions with optional filters."""
    query = db.query(Transaction).filter(Transaction.user_id == user_id)
    query = _apply_transaction_filters(
        query,
        category_id=category_id,
        transaction_type=transaction_type,
        start_date=start_date,
        end_date=end_date,
        search=search,
        category_name=category_name,
        needs_review=needs_review,
        payment_method=payment_method,
    )

    total = query.count()

    # Determine sort order
    sort_column = Transaction.date
    if sort_by == "amount":
        sort_column = Transaction.amount
    elif sort_by == "transaction_date":
        sort_column = Transaction.date
    elif sort_by == "description":
        sort_column = Transaction.description

    if sort_order == "asc":
        query = query.order_by(sort_column.asc())
    else:
        query = query.order_by(sort_column.desc())

    transactions = (
        query.offset((page - 1) * page_size)
        .limit(page_size)
        .all()
    )

    return transactions, total


def get_transaction_by_id(db: Session, transaction_id: int, user_id: int) -> Optional[Transaction]:
    """Get a single transaction by ID."""
    return db.query(Transaction).filter(
        and_(Transaction.id == transaction_id, Transaction.user_id == user_id)
    ).first()


def create_transaction(db: Session, txn_data: TransactionCreate) -> Transaction:
    """Create a new transaction."""
    txn = Transaction(
        user_id=txn_data.user_id,
        date=txn_data.date,
        description=txn_data.description,
        amount=txn_data.amount,
        transaction_type=txn_data.transaction_type,
        balance=txn_data.balance,
        reference_number=txn_data.reference_number,
        bank_name=txn_data.bank_name,
        account_number=txn_data.account_number,
        category_id=txn_data.category_id,
    )
    db.add(txn)
    db.commit()
    db.refresh(txn)
    return txn


def update_transaction(db: Session, transaction_id: int, user_id: int, update_data: TransactionUpdate) -> Optional[Transaction]:
    """Update a transaction."""
    txn = get_transaction_by_id(db, transaction_id, user_id)
    if not txn:
        return None

    update_dict = update_data.model_dump(exclude_unset=True)
    update_dict.pop("category_name", None)

    # When user explicitly sets category, mark as manually confirmed
    if "category_id" in update_dict and update_dict["category_id"] is not None:
        update_dict["confidence_score"] = 1.0
        update_dict["classification_source"] = "manual"

    for field, value in update_dict.items():
        setattr(txn, field, value)

    db.commit()
    db.refresh(txn)
    return txn


def delete_transaction(db: Session, transaction_id: int, user_id: int) -> bool:
    """Delete a transaction. Returns True if deleted."""
    txn = get_transaction_by_id(db, transaction_id, user_id)
    if not txn:
        return False
    db.delete(txn)
    db.commit()
    return True
