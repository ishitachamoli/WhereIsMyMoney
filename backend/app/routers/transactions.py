"""Transaction CRUD endpoints."""
import math
from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session
from typing import Optional, List
from datetime import datetime

from app.core.database import get_db
from app.core.auth import get_current_user
from app.models.user import User
from app.models.category import Category
from app.models.transaction import Transaction as TransactionModel
from app.schemas.transaction import (
    TransactionCreate,
    TransactionUpdate,
    TransactionResponse,
    TransactionListResponse,
    TotalsResponse,
    ManualTransactionCreate,
)
from app.services import transaction_service
from app.services.merchant_extractor import extract_merchant

router = APIRouter(prefix="/transactions", tags=["transactions"])


def _build_transaction_response(t: TransactionModel) -> TransactionResponse:
    """Build a TransactionResponse from a Transaction model instance."""
    merchant = extract_merchant(t.description) if t.description else None
    return TransactionResponse(
        id=t.id,
        account_id=t.bank_statement_id or 0,
        transaction_date=t.date.isoformat() if t.date else "",
        description=t.description,
        amount=t.amount,
        transaction_type=t.transaction_type.value if hasattr(t.transaction_type, 'value') else str(t.transaction_type),
        balance=t.balance,
        reference_number=t.reference_number,
        merchant_name=merchant,
        category=t.category.name if t.category else "Uncategorized",
        subcategory=None,
        confidence_score=t.confidence_score if t.confidence_score is not None else 1.0,
        classification_tier=t.classification_source or "rule",
        source=t.source or "upload",
        currency=t.currency if t.currency else "INR",
        tags=None,
        is_recurring=False,
        notes=None,
        metadata=None,
        created_at=t.created_at.isoformat() if t.created_at else "",
        updated_at=t.updated_at.isoformat() if t.updated_at else "",
    )


@router.get("", response_model=TransactionListResponse)
def list_transactions(
    current_user: User = Depends(get_current_user),
    page: int = Query(1, ge=1),
    page_size: int = Query(50, ge=1, le=200),
    category: Optional[str] = None,
    category_id: Optional[int] = None,
    transaction_type: Optional[str] = None,
    start_date: Optional[datetime] = None,
    end_date: Optional[datetime] = None,
    search: Optional[str] = None,
    sort_by: Optional[str] = None,
    sort_order: Optional[str] = None,
    needs_review: Optional[bool] = None,
    payment_method: Optional[str] = None,
    db: Session = Depends(get_db),
):
    """List transactions with pagination and filtering."""
    transactions, total = transaction_service.get_transactions(
        db, current_user.id, page, page_size, category_id, transaction_type,
        start_date, end_date, search, category_name=category,
        sort_by=sort_by, sort_order=sort_order, needs_review=needs_review,
        payment_method=payment_method,
    )

    totals_raw = transaction_service.get_transaction_totals(
        db, current_user.id, category_id=category_id, transaction_type=transaction_type,
        start_date=start_date, end_date=end_date, search=search, category_name=category,
        needs_review=needs_review, payment_method=payment_method,
    )

    from app.services.currency_helper import get_dominant_currency
    totals = TotalsResponse(
        credit_amount=totals_raw["credit_amount"],
        debit_amount=totals_raw["debit_amount"],
        net_amount=totals_raw["net_amount"],
        currency=get_dominant_currency(db, current_user.id),
    )

    total_pages = math.ceil(total / page_size) if page_size > 0 else 0

    return TransactionListResponse(
        items=[_build_transaction_response(t) for t in transactions],
        total=total,
        page=page,
        page_size=page_size,
        total_pages=total_pages,
        totals=totals,
    )


@router.get("/{transaction_id}", response_model=TransactionResponse)
def get_transaction(
    transaction_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Get a single transaction by ID."""
    txn = transaction_service.get_transaction_by_id(db, transaction_id, current_user.id)
    if not txn:
        raise HTTPException(status_code=404, detail="Transaction not found")
    return _build_transaction_response(txn)


@router.post("", response_model=TransactionResponse, status_code=201)
def create_transaction(
    txn_data: ManualTransactionCreate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Create a new transaction manually (cash/manual entry)."""
    from app.models.transaction import TransactionType

    # Parse the transaction date (defaults to today)
    if txn_data.transaction_date:
        try:
            parsed_date = datetime.fromisoformat(txn_data.transaction_date)
        except ValueError:
            try:
                parsed_date = datetime.strptime(txn_data.transaction_date, "%Y-%m-%d")
            except ValueError:
                raise HTTPException(status_code=400, detail="Invalid date format. Use YYYY-MM-DD.")
    else:
        parsed_date = datetime.utcnow()

    # Resolve category by name
    category_id = None
    if txn_data.category_name:
        cat = db.query(Category).filter(
            Category.name == txn_data.category_name,
            (Category.user_id == current_user.id) | (Category.is_system == True),
        ).first()
        if cat:
            category_id = cat.id

    # Ensure amount is positive (store absolute value)
    amount = abs(txn_data.amount)

    txn = TransactionModel(
        user_id=current_user.id,
        date=parsed_date,
        description=txn_data.description,
        amount=amount,
        transaction_type=txn_data.transaction_type,
        source=txn_data.source,
        category_id=category_id,
        confidence_score=1.0,
        classification_source="manual",
    )
    db.add(txn)
    db.commit()
    db.refresh(txn)
    return _build_transaction_response(txn)


@router.delete("/data/clear", status_code=200)
def clear_all_data(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Delete ALL user-related data: classification jobs, learned rules, budgets, 
    categories (user-created only), transactions, and bank statements."""
    from app.models.transaction import Transaction
    from app.models.bank_statement import BankStatement
    from app.models.classification_job import ClassificationJob
    from app.models.learned_rule import LearnedRule
    from app.models.budget import Budget
    from app.models.category import Category
    
    # Count records to delete (for response)
    job_count = db.query(ClassificationJob).filter(
        ClassificationJob.user_id == current_user.id
    ).count()
    
    rule_count = db.query(LearnedRule).filter(
        LearnedRule.user_id == current_user.id
    ).count()
    
    budget_count = db.query(Budget).filter(
        Budget.user_id == current_user.id
    ).count()
    
    # User-created categories only (is_system=False)
    category_count = db.query(Category).filter(
        Category.user_id == current_user.id,
        Category.is_system == False
    ).count()
    
    transaction_count = db.query(Transaction).filter(
        Transaction.user_id == current_user.id
    ).count()
    
    statement_count = db.query(BankStatement).filter(
        BankStatement.user_id == current_user.id
    ).count()
    
    # Delete in correct order to respect FK constraints:
    # 1. ClassificationJob (references bank_statements and users)
    db.query(ClassificationJob).filter(
        ClassificationJob.user_id == current_user.id
    ).delete(synchronize_session="fetch")
    
    # 2. LearnedRule (references users)
    db.query(LearnedRule).filter(
        LearnedRule.user_id == current_user.id
    ).delete(synchronize_session="fetch")
    
    # 3. Budget (references users and categories)
    db.query(Budget).filter(
        Budget.user_id == current_user.id
    ).delete(synchronize_session="fetch")
    
    # 4. User-created Categories (is_system=False, references users)
    db.query(Category).filter(
        Category.user_id == current_user.id,
        Category.is_system == False
    ).delete(synchronize_session="fetch")
    
    # 5. Transactions (references users and bank_statements)
    db.query(Transaction).filter(
        Transaction.user_id == current_user.id
    ).delete(synchronize_session="fetch")
    
    # 6. BankStatements (references users, may be orphaned)
    db.query(BankStatement).filter(
        BankStatement.user_id == current_user.id
    ).delete(synchronize_session="fetch")
    
    db.commit()
    
    return {
        "message": "All user data cleared",
        "deleted_classification_jobs": job_count,
        "deleted_learned_rules": rule_count,
        "deleted_budgets": budget_count,
        "deleted_categories": category_count,
        "deleted_transactions": transaction_count,
        "deleted_statements": statement_count,
    }


class BulkUpdateFilters(BaseModel):
    """Filters for bulk transaction update by criteria."""
    category: Optional[str] = None
    transaction_type: Optional[str] = None
    payment_method: Optional[str] = None
    search: Optional[str] = None
    needs_review: Optional[bool] = None


class BulkUpdateRequest(BaseModel):
    """Request model for bulk transaction update."""
    transaction_ids: Optional[List[int]] = Field(None, min_length=1, max_length=500)
    filters: Optional[BulkUpdateFilters] = None
    category_name: str = Field(..., min_length=1)


@router.put("/bulk-update")
def bulk_update_transactions(
    body: BulkUpdateRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Bulk update transactions with a given category. Creates learned rules.
    
    Accepts either transaction_ids (for selected transactions) or filters
    (for bulk operation on all matching transactions).
    """
    # Validate input
    if not body.transaction_ids and not body.filters:
        raise HTTPException(
            status_code=400,
            detail="Either transaction_ids or filters must be provided"
        )
    
    cat = db.query(Category).filter(
        Category.name == body.category_name,
        (Category.user_id == current_user.id) | (Category.is_system == True),
    ).first()
    if not cat:
        raise HTTPException(status_code=400, detail=f"Category '{body.category_name}' not found")

    # Build transaction query based on input
    from sqlalchemy import or_
    if body.transaction_ids:
        # Update specific transaction IDs
        txn_query = db.query(TransactionModel).filter(
            TransactionModel.id.in_(body.transaction_ids),
            TransactionModel.user_id == current_user.id,
        )
    else:
        # Build query from filter criteria
        txn_query = db.query(TransactionModel).filter(
            TransactionModel.user_id == current_user.id
        )
        
        if body.filters.category:
            if body.filters.category.lower() == "uncategorized":
                txn_query = txn_query.filter(TransactionModel.category_id.is_(None))
            else:
                txn_query = txn_query.join(
                    Category, TransactionModel.category_id == Category.id
                ).filter(Category.name.ilike(f"%{body.filters.category}%"))
        
        if body.filters.transaction_type:
            txn_query = txn_query.filter(
                TransactionModel.transaction_type == body.filters.transaction_type
            )
        
        if body.filters.search:
            txn_query = txn_query.filter(
                TransactionModel.description.ilike(f"%{body.filters.search}%")
            )
        
        if body.filters.payment_method:
            method_keywords = {
                "UPI": ["UPI", "upi"],
                "NEFT": ["NEFT", "neft"],
                "IMPS": ["IMPS", "imps"],
                "POS": ["POS", "pos"],
                "RTGS": ["RTGS", "rtgs"],
                "ATM": ["ATM", "atm"],
                "Auto-Debit": ["AUTO", "auto debit", "SI-"],
                "Cheque": ["CHQ", "cheque", "CHEQUE"],
            }
            keywords = method_keywords.get(body.filters.payment_method, [body.filters.payment_method])
            conditions = [TransactionModel.description.ilike(f"%{kw}%") for kw in keywords]
            txn_query = txn_query.filter(or_(*conditions))
        
        if body.filters.needs_review:
            txn_query = txn_query.filter(TransactionModel.confidence_score < 0.7)

    # Fetch transactions for learned rule creation
    txns = txn_query.all()

    # Create learned rules from the transactions being updated
    from app.services.classification.learned_rules import create_learned_rule
    for txn in txns:
        if txn.description:
            create_learned_rule(db, current_user.id, txn.description, body.category_name)

    # Extract transaction IDs to avoid SQLAlchemy join+update error
    # (Can't call .update() on a query that has .join())
    txn_ids = [t.id for t in txns]
    
    # Update all matching transactions using IDs (no join needed)
    updated_count = db.query(TransactionModel).filter(
        TransactionModel.id.in_(txn_ids),
        TransactionModel.user_id == current_user.id,
    ).update(
        {
            TransactionModel.category_id: cat.id,
            TransactionModel.confidence_score: 1.0,
            TransactionModel.classification_source: "manual",
        },
        synchronize_session="fetch",
    )
    db.commit()

    return {
        "message": f"Updated {updated_count} transactions to '{body.category_name}'",
        "updated_count": updated_count,
    }


@router.put("/{transaction_id}", response_model=TransactionResponse)
def update_transaction(
    transaction_id: int,
    update_data: TransactionUpdate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Update a transaction. When category changes, creates a learned rule."""
    if update_data.category_name and not update_data.category_id:
        cat = db.query(Category).filter(
            Category.name == update_data.category_name,
            (Category.user_id == current_user.id) | (Category.is_system == True),
        ).first()
        if cat:
            update_data.category_id = cat.id
        else:
            raise HTTPException(status_code=400, detail=f"Category '{update_data.category_name}' not found")

    # Get the transaction before update to check if category changed
    existing_txn = transaction_service.get_transaction_by_id(db, transaction_id, current_user.id)
    if not existing_txn:
        raise HTTPException(status_code=404, detail="Transaction not found")

    # Determine the new category name for learned rule creation
    new_category_name = update_data.category_name
    if not new_category_name and update_data.category_id:
        cat = db.query(Category).filter(Category.id == update_data.category_id).first()
        if cat:
            new_category_name = cat.name

    # If category is changing, create a learned rule
    if new_category_name and existing_txn.description:
        old_category_name = existing_txn.category.name if existing_txn.category else None
        if old_category_name != new_category_name:
            from app.services.classification.learned_rules import create_learned_rule
            create_learned_rule(db, current_user.id, existing_txn.description, new_category_name)

    txn = transaction_service.update_transaction(db, transaction_id, current_user.id, update_data)
    if not txn:
        raise HTTPException(status_code=404, detail="Transaction not found")
    return _build_transaction_response(txn)


@router.delete("/{transaction_id}", status_code=204)
def delete_transaction(
    transaction_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Delete a transaction."""
    deleted = transaction_service.delete_transaction(db, transaction_id, current_user.id)
    if not deleted:
        raise HTTPException(status_code=404, detail="Transaction not found")


# ─── Transaction Explanation Endpoints ─────────────────────────────────────────


class ExplainResponse(BaseModel):
    """AI explanation of a single transaction."""
    explanation: str
    recipient_or_sender: Optional[str] = None
    payment_method: Optional[str] = None
    reference: Optional[str] = None
    category_suggestion: Optional[str] = None
    confidence: float
    direction: Optional[str] = None
    card_reference: Optional[str] = None
    service: Optional[str] = None


class ExplainBatchRequest(BaseModel):
    """Request model for batch transaction explanation."""
    transaction_ids: Optional[List[int]] = Field(None, max_length=100)
    category: Optional[str] = None
    limit: int = Field(50, ge=1, le=200)


class ExplainBatchItem(BaseModel):
    """Single item in a batch explanation response."""
    transaction_id: int
    description: str
    amount: float
    transaction_type: str
    current_category: str
    explanation: ExplainResponse


class ExplainBatchResponse(BaseModel):
    """Response for batch transaction explanation."""
    items: List[ExplainBatchItem]
    total: int


@router.post("/explain-batch", response_model=ExplainBatchResponse)
def explain_transactions_batch(
    body: ExplainBatchRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Get AI explanations for multiple transactions at once."""
    from app.services.transaction_explainer import explain_transaction

    query = db.query(TransactionModel).filter(TransactionModel.user_id == current_user.id)

    if body.transaction_ids:
        query = query.filter(TransactionModel.id.in_(body.transaction_ids))
    elif body.category:
        if body.category.lower() == "uncategorized":
            query = query.filter(TransactionModel.category_id.is_(None))
        else:
            cat = db.query(Category).filter(
                Category.name == body.category,
                (Category.user_id == current_user.id) | (Category.is_system == True),
            ).first()
            if cat:
                query = query.filter(TransactionModel.category_id == cat.id)
            else:
                raise HTTPException(status_code=400, detail=f"Category '{body.category}' not found")
    else:
        raise HTTPException(
            status_code=400,
            detail="Provide either transaction_ids or category filter",
        )

    transactions = query.limit(body.limit).all()

    items = []
    for txn in transactions:
        date_str = txn.date.strftime("%b %d, %Y") if txn.date else None
        txn_type = txn.transaction_type.value if hasattr(txn.transaction_type, "value") else str(txn.transaction_type)
        current_category = txn.category.name if txn.category else "Uncategorized"

        result = explain_transaction(
            description=txn.description,
            amount=txn.amount,
            transaction_type=txn_type,
            date=date_str,
            category=current_category,
        )

        items.append(ExplainBatchItem(
            transaction_id=txn.id,
            description=txn.description,
            amount=txn.amount,
            transaction_type=txn_type,
            current_category=current_category,
            explanation=ExplainResponse(
                explanation=result.explanation,
                recipient_or_sender=result.recipient_or_sender,
                payment_method=result.payment_method,
                reference=result.reference,
                category_suggestion=result.category_suggestion,
                confidence=result.confidence,
                direction=result.direction,
                card_reference=result.card_reference,
                service=result.service,
            ),
        ))

    return ExplainBatchResponse(items=items, total=len(items))


@router.post("/{transaction_id}/explain", response_model=ExplainResponse)
def explain_transaction_endpoint(
    transaction_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Get an AI-powered explanation of a transaction's description."""
    from app.services.transaction_explainer import explain_transaction

    txn = transaction_service.get_transaction_by_id(db, transaction_id, current_user.id)
    if not txn:
        raise HTTPException(status_code=404, detail="Transaction not found")

    date_str = txn.date.strftime("%b %d, %Y") if txn.date else None
    txn_type = txn.transaction_type.value if hasattr(txn.transaction_type, "value") else str(txn.transaction_type)
    current_category = txn.category.name if txn.category else None

    result = explain_transaction(
        description=txn.description,
        amount=txn.amount,
        transaction_type=txn_type,
        date=date_str,
        category=current_category,
    )

    return ExplainResponse(
        explanation=result.explanation,
        recipient_or_sender=result.recipient_or_sender,
        payment_method=result.payment_method,
        reference=result.reference,
        category_suggestion=result.category_suggestion,
        confidence=result.confidence,
        direction=result.direction,
        card_reference=result.card_reference,
        service=result.service,
    )
