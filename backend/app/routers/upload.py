"""File upload endpoint for bank statements (CSV and PDF)."""
import logging
import time
from collections import defaultdict
from datetime import datetime, timezone
from typing import Optional

from fastapi import APIRouter, BackgroundTasks, Depends, Form, HTTPException, UploadFile, File
from sqlalchemy.orm import Session

from app.core.database import get_db, get_session_local
from app.core.config import settings
from app.core.auth import get_current_user
from app.models.bank_statement import BankStatement
from app.models.classification_job import ClassificationJob
from app.models.user import User
from app.models.category import Category
from app.models.transaction import Transaction, TransactionType
from app.schemas.upload import (
    UploadResponse,
    UploadSummary,
    TransactionResponse,
    CategoryBreakdownResponse,
    BankStatementResponse,
)
from app.services.bank_parser import (
    parse_csv_statement,
    parse_pdf_statement,
    parse_excel_statement,
    BankDetectionError,
    ParsingError,
)
from app.services.classification.pipeline import ClassificationPipeline, PipelineConfig

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/upload", tags=["upload"])

ALLOWED_EXTENSIONS = {".csv", ".pdf", ".xls", ".xlsx"}
MAX_FILE_SIZE = settings.MAX_UPLOAD_SIZE_MB * 1024 * 1024


def _decode_csv_bytes(content_bytes: bytes) -> str:
    """Decode CSV file bytes with encoding fallback chain.

    Indian bank statements may use various encodings. Try UTF-8 first (most common),
    then fall back to common Windows/legacy encodings that handle extended Latin characters.
    """
    # Try UTF-8 first (strict to detect encoding issues)
    try:
        return content_bytes.decode("utf-8")
    except (UnicodeDecodeError, ValueError):
        pass

    # Try UTF-8 with BOM
    try:
        return content_bytes.decode("utf-8-sig")
    except (UnicodeDecodeError, ValueError):
        pass

    # Try Windows cp1252 (common in Indian bank exports from Windows systems)
    try:
        return content_bytes.decode("cp1252")
    except (UnicodeDecodeError, ValueError):
        pass

    # Latin-1 always succeeds (maps bytes 0x00-0xFF to U+0000-U+00FF)
    return content_bytes.decode("latin-1")


def _get_rule_only_pipeline() -> ClassificationPipeline:
    """Initialize classification pipeline with rules only (no ML, no LLM)."""
    config = PipelineConfig(
        enable_ml=False,
        enable_llm=False,
    )
    return ClassificationPipeline(config=config)


def _get_ml_pipeline() -> ClassificationPipeline:
    """Initialize classification pipeline with DistilBART model for ML classification."""
    config = PipelineConfig(
        enable_ml=True,
        enable_llm=False,
    )
    return ClassificationPipeline(config=config)


def _resolve_category_id(db: Session, category_name: str, user_id: int) -> int | None:
    """Map a classification category name to a category_id in the DB."""
    category = (
        db.query(Category)
        .filter(
            Category.name == category_name,
            (Category.user_id == user_id) | (Category.is_system == True),
        )
        .first()
    )
    if category:
        return category.id
    # Try partial/fuzzy matching (handles "Transfers" vs "Transfer", etc.)
    category = (
        db.query(Category)
        .filter(
            Category.name.ilike(f"%{category_name}%"),
            (Category.user_id == user_id) | (Category.is_system == True),
        )
        .first()
    )
    if category:
        return category.id
    # Try the other direction (DB name contains in classification name)
    all_categories = (
        db.query(Category)
        .filter((Category.user_id == user_id) | (Category.is_system == True))
        .all()
    )
    name_lower = category_name.lower()
    for cat in all_categories:
        if cat.name.lower() in name_lower or name_lower in cat.name.lower():
            return cat.id
    return None


def _build_category_lookup(db: Session, user_id: int) -> dict[str, int]:
    """Pre-load all categories for a user into a fast lookup dict.

    Builds a case-insensitive mapping from category name variations to category IDs.
    This eliminates N+1 DB queries when resolving categories in loops.

    Returns:
        Dict mapping lowercase category name -> category ID.
    """
    all_categories = (
        db.query(Category)
        .filter((Category.user_id == user_id) | (Category.is_system == True))
        .all()
    )
    lookup: dict[str, int] = {}
    for cat in all_categories:
        lookup[cat.name.lower()] = cat.id
    return lookup


def _resolve_category_id_fast(category_name: str, lookup: dict[str, int]) -> int | None:
    """Resolve category name to ID using pre-built lookup dict (no DB queries).

    Tries exact match first, then substring matching in both directions.
    """
    name_lower = category_name.lower()

    # Exact match
    if name_lower in lookup:
        return lookup[name_lower]

    # Partial match: lookup name contains category_name
    for db_name, cat_id in lookup.items():
        if name_lower in db_name:
            return cat_id

    # Reverse partial: category_name contains lookup name
    for db_name, cat_id in lookup.items():
        if db_name in name_lower:
            return cat_id

    return None


def _run_ml_classification_background(
    job_id: str,
    transaction_ids: list[int],
    user_id: int,
) -> None:
    """Background task: Run ML classification on transactions that rule-engine couldn't classify well.

    Performance optimizations vs the naive approach:
    1. Calls MLClassifier.classify_batch directly (skips redundant rule-engine re-run)
    2. Pre-builds category lookup dict (eliminates N+1 DB queries)
    3. MLClassifier uses true cross-text NLI batching internally

    Updates the ClassificationJob progress as it processes batches, allowing
    the frontend to poll and show real-time progress.
    """
    from app.services.classification.ml_classifier import MLClassifier

    SessionLocal = get_session_local()
    db = SessionLocal()

    try:
        overall_start = time.time()

        # Mark job as running
        job = db.query(ClassificationJob).filter(ClassificationJob.id == job_id).first()
        if not job:
            logger.error(f"Classification job {job_id} not found")
            return
        job.status = "running"
        db.commit()

        # Load transactions
        transactions = (
            db.query(Transaction)
            .filter(Transaction.id.in_(transaction_ids))
            .all()
        )

        if not transactions:
            job.status = "completed"
            job.classified_transactions = job.total_transactions
            job.completed_at = datetime.now(timezone.utc)
            db.commit()
            return

        logger.info(
            f"Job {job_id}: Starting ML classification for {len(transactions)} transactions"
        )

        # Pre-build category lookup (eliminates N+1 DB queries)
        category_lookup = _build_category_lookup(db, user_id)

        # Call MLClassifier directly — skip the full pipeline to avoid
        # redundant rule-engine re-run (these transactions already failed rules)
        ml_classifier = MLClassifier()

        # Prepare all descriptions and amounts upfront
        all_descriptions: list[str] = []
        all_amounts: list[Optional[float]] = []
        for txn in transactions:
            all_descriptions.append(txn.description)
            amount = -txn.amount if txn.transaction_type == TransactionType.DEBIT else txn.amount
            all_amounts.append(amount)

        # Run ML classification in one batched call (true cross-text batching)
        ml_start = time.time()
        ml_results = ml_classifier.classify_batch(all_descriptions, all_amounts)
        ml_elapsed = time.time() - ml_start

        logger.info(
            f"Job {job_id}: ML inference completed in {ml_elapsed:.1f}s "
            f"({ml_elapsed / max(len(transactions), 1) * 1000:.0f} ms/tx)"
        )

        # Apply results and update DB (using pre-built category lookup)
        update_start = time.time()
        updated_count = 0
        for txn, ml_result in zip(transactions, ml_results):
            if ml_result.confidence > (txn.confidence_score or 0):
                category_id = _resolve_category_id_fast(ml_result.category, category_lookup)
                if category_id:
                    txn.category_id = category_id
                txn.confidence_score = ml_result.confidence
                txn.classification_source = ml_result.source if ml_result.source != "unknown" else "ml_classifier"
                updated_count += 1

        # Single commit for all updates
        job.classified_transactions = len(transactions)
        job.status = "completed"
        job.completed_at = datetime.now(timezone.utc)
        db.commit()

        update_elapsed = time.time() - update_start
        overall_elapsed = time.time() - overall_start

        logger.info(
            f"Job {job_id}: completed in {overall_elapsed:.1f}s total "
            f"(ML={ml_elapsed:.1f}s, DB update={update_elapsed:.1f}s, "
            f"{updated_count}/{len(transactions)} transactions improved)"
        )

    except Exception as e:
        logger.error(f"Classification job {job_id} failed: {e}")
        try:
            job = db.query(ClassificationJob).filter(ClassificationJob.id == job_id).first()
            if job:
                job.status = "failed"
                job.error = str(e)[:500]
                job.completed_at = datetime.now(timezone.utc)
                db.commit()
        except Exception:
            pass
    finally:
        db.close()


@router.post("", response_model=UploadResponse)
def upload_statement(
    file: UploadFile = File(...),
    bank: Optional[str] = Form(None),
    background_tasks: BackgroundTasks = BackgroundTasks(),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """
    Upload a bank statement file (CSV, Excel, or PDF).
    Auto-detects the bank format and parses transactions.
    Optionally accepts a 'bank' hint (e.g., 'hdfc', 'icici') to skip detection.
    Use 'auto' or omit for automatic detection with generic fallback.

    Rule-engine classification is applied synchronously for immediate results.
    ML classification runs in background — poll /api/v1/jobs/classification/{id} for progress.
    """
    user_id = current_user.id
    start_time = time.time()

    # Validate file extension
    filename = file.filename or "unknown"
    extension = "." + filename.rsplit(".", 1)[-1].lower() if "." in filename else ""

    if extension not in ALLOWED_EXTENSIONS:
        raise HTTPException(
            status_code=400,
            detail=f"Unsupported file type: {extension}. Allowed: {', '.join(ALLOWED_EXTENSIONS)}"
        )

    # Read file content
    content_bytes = file.file.read()
    if len(content_bytes) > MAX_FILE_SIZE:
        raise HTTPException(
            status_code=400,
            detail=f"File too large. Maximum size: {settings.MAX_UPLOAD_SIZE_MB}MB"
        )

    if len(content_bytes) == 0:
        raise HTTPException(status_code=400, detail="File is empty")

    # If user provided a specific bank hint, prepend it to filename for detection
    bank_hint = bank.strip().lower() if bank and bank.strip().lower() != "auto" else ""
    effective_filename = f"{bank_hint}_{filename}" if bank_hint else filename

    # Parse based on file type
    try:
        if extension == ".csv":
            content_str = _decode_csv_bytes(content_bytes)
            bank_name, parsed_transactions = parse_csv_statement(content_str, effective_filename)
        elif extension in {".xls", ".xlsx"}:
            bank_name, parsed_transactions = parse_excel_statement(content_bytes, effective_filename)
        else:  # .pdf
            bank_name, parsed_transactions = parse_pdf_statement(content_bytes, effective_filename)
    except BankDetectionError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except ParsingError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        logger.error(f"Unexpected error parsing file {filename}: {e}")
        raise HTTPException(status_code=500, detail="Internal error processing file")

    if not parsed_transactions:
        raise HTTPException(
            status_code=400,
            detail="No transactions could be parsed from the file. Check the file format."
        )

    # Calculate statement summary
    total_credits = sum(t.amount for t in parsed_transactions if t.transaction_type == "credit")
    total_debits = sum(t.amount for t in parsed_transactions if t.transaction_type == "debit")
    dates = [t.date for t in parsed_transactions]
    start_date = min(dates) if dates else None
    end_date = max(dates) if dates else None

    # Create bank statement record
    bank_statement = BankStatement(
        user_id=user_id,
        filename=filename,
        bank_name=bank_name,
        file_type=extension.lstrip("."),
        transaction_count=len(parsed_transactions),
        total_credits=round(total_credits, 2),
        total_debits=round(total_debits, 2),
        start_date=start_date,
        end_date=end_date,
    )
    db.add(bank_statement)
    db.flush()

    # SYNC: Rule-engine classification only (fast, <1ms per transaction)
    pipeline = _get_rule_only_pipeline()
    classification_data = []
    for pt in parsed_transactions:
        classification_data.append({
            "description": pt.description,
            "amount": -pt.amount if pt.transaction_type == "debit" else pt.amount,
            "transaction_type": pt.transaction_type,
        })

    classification_results = pipeline.classify_batch(classification_data)

    db_transactions: list[Transaction] = []
    ml_candidate_ids: list[int] = []

    for pt, cls_result in zip(parsed_transactions, classification_results):
        category_id = _resolve_category_id(db, cls_result.category, user_id)
        txn = Transaction(
            user_id=user_id,
            bank_statement_id=bank_statement.id,
            date=pt.date,
            description=pt.description,
            amount=pt.amount,
            transaction_type=TransactionType(pt.transaction_type),
            balance=pt.balance,
            reference_number=pt.reference_number,
            bank_name=pt.bank_name,
            category_id=category_id,
            confidence_score=cls_result.confidence,
            classification_source=cls_result.source if cls_result.source != "unknown" else "rule",
            currency=pt.currency,
        )
        db.add(txn)
        db_transactions.append(txn)

    db.flush()

    # Identify transactions needing ML classification (low confidence from rules)
    for txn, cls_result in zip(db_transactions, classification_results):
        if cls_result.confidence < 0.7:
            ml_candidate_ids.append(txn.id)

    # Create classification job for background ML processing
    classification_job_id: Optional[str] = None
    if ml_candidate_ids:
        job = ClassificationJob(
            user_id=user_id,
            bank_statement_id=bank_statement.id,
            total_transactions=len(ml_candidate_ids),
            classified_transactions=0,
            status="pending",
        )
        db.add(job)
        db.flush()
        classification_job_id = job.id

    db.commit()
    db.refresh(bank_statement)
    for txn in db_transactions:
        db.refresh(txn)

    # Schedule background ML classification
    if classification_job_id and ml_candidate_ids:
        background_tasks.add_task(
            _run_ml_classification_background,
            classification_job_id,
            ml_candidate_ids,
            user_id,
        )

    logger.info(
        f"Successfully parsed {len(parsed_transactions)} transactions "
        f"from {bank_name} {extension} file: {filename} "
        f"({len(ml_candidate_ids)} queued for ML classification)"
    )

    # Build the rich response the frontend expects
    processing_time = round(time.time() - start_time, 2)

    # Build category breakdown
    category_totals: dict[str, dict] = defaultdict(lambda: {"amount": 0.0, "count": 0})
    unique_categories: set[str] = set()
    low_confidence_count = 0

    transaction_responses: list[TransactionResponse] = []
    for txn, cls_result in zip(db_transactions, classification_results):
        cat_name = cls_result.category
        unique_categories.add(cat_name)
        category_totals[cat_name]["amount"] += txn.amount
        category_totals[cat_name]["count"] += 1

        if cls_result.confidence < 0.5:
            low_confidence_count += 1

        now_str = txn.created_at.isoformat() if txn.created_at else ""
        transaction_responses.append(TransactionResponse(
            id=txn.id,
            account_id=bank_statement.id,
            transaction_date=txn.date.isoformat() if txn.date else "",
            description=txn.description,
            amount=txn.amount,
            transaction_type=txn.transaction_type.value,
            balance=txn.balance,
            reference_number=txn.reference_number,
            merchant_name=None,
            category=cls_result.category,
            subcategory=cls_result.subcategory if hasattr(cls_result, 'subcategory') else None,
            confidence_score=cls_result.confidence,
            classification_tier=cls_result.source if cls_result.source != "unknown" else "rule",
            currency=txn.currency if txn.currency else "INR",
            tags=None,
            is_recurring=False,
            notes=None,
            metadata=None,
            created_at=now_str,
            updated_at=now_str,
        ))

    total_expense_amount = sum(
        v["amount"] for k, v in category_totals.items()
    )
    category_breakdown_list: list[CategoryBreakdownResponse] = []
    for cat_name, data in sorted(category_totals.items(), key=lambda x: x[1]["amount"], reverse=True):
        pct = (data["amount"] / total_expense_amount * 100) if total_expense_amount > 0 else 0
        avg = data["amount"] / data["count"] if data["count"] > 0 else 0
        category_breakdown_list.append(CategoryBreakdownResponse(
            category=cat_name,
            total_amount=round(data["amount"], 2),
            percentage=round(pct, 1),
            transaction_count=data["count"],
            average_transaction=round(avg, 2),
        ))

    warnings: list[str] = []
    if low_confidence_count > 0:
        warnings.append(f"{low_confidence_count} transactions have low classification confidence and may need review.")
    if ml_candidate_ids:
        warnings.append(f"AI is classifying {len(ml_candidate_ids)} transactions in the background. Check progress on your dashboard.")

    return UploadResponse(
        upload_id=bank_statement.id,
        status="success",
        summary=UploadSummary(
            total_transactions=len(db_transactions),
            date_range={
                "start": start_date.isoformat() if start_date else "",
                "end": end_date.isoformat() if end_date else "",
            },
            total_income=round(total_credits, 2),
            total_expenses=round(total_debits, 2),
            net_cash_flow=round(total_credits - total_debits, 2),
            categories_detected=len(unique_categories),
            transactions_needing_review=low_confidence_count,
            processing_time_seconds=processing_time,
        ),
        transactions=transaction_responses,
        category_breakdown=category_breakdown_list,
        warnings=warnings if warnings else None,
        classification_job_id=classification_job_id,
    )


@router.get("/statements", response_model=list[BankStatementResponse])
def list_statements(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """List all uploaded bank statements for a user."""
    statements = (
        db.query(BankStatement)
        .filter(BankStatement.user_id == current_user.id)
        .order_by(BankStatement.upload_date.desc())
        .all()
    )
    return [BankStatementResponse.model_validate(s) for s in statements]
