"""Classification API router.

Endpoints:
  POST /api/classify        — Classify a single transaction
  POST /api/classify/batch  — Classify multiple transactions
  POST /api/classify/feedback — Submit user correction
  GET  /api/classify/stats  — Classification accuracy and performance stats
"""

from __future__ import annotations

import logging
from typing import Optional

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field

from app.services.classification.feedback import FeedbackEntry, FeedbackStore
from app.services.classification.pipeline import (
    ClassificationPipeline,
    PipelineConfig,
)

logger = logging.getLogger(__name__)

router = APIRouter()

# Module-level singletons (initialized once per process)
_pipeline: Optional[ClassificationPipeline] = None
_feedback_store: Optional[FeedbackStore] = None


def get_pipeline() -> ClassificationPipeline:
    global _pipeline
    if _pipeline is None:
        config = PipelineConfig(
            enable_ml=True,
            enable_llm=True,
        )
        _pipeline = ClassificationPipeline(config=config)
    return _pipeline


def get_feedback_store() -> FeedbackStore:
    global _feedback_store
    if _feedback_store is None:
        _feedback_store = FeedbackStore()
    return _feedback_store


# ─── Request/Response Models ─────────────────────────────────────────────────


class TransactionInput(BaseModel):
    """Input model for a single transaction to classify."""

    description: str = Field(..., min_length=1, max_length=500, description="Transaction description from bank statement")
    amount: Optional[float] = Field(None, description="Transaction amount. Positive=credit, negative=debit.")
    transaction_type: Optional[str] = Field(None, pattern="^(debit|credit)$", description="Explicit debit/credit hint")


class ClassificationResponse(BaseModel):
    """Response model for a classified transaction."""

    category: str
    subcategory: Optional[str] = None
    merchant: Optional[str] = None
    confidence: float
    confidence_level: str
    source: str
    needs_review: bool
    reasoning: Optional[str] = None


class BatchClassifyRequest(BaseModel):
    """Input model for batch classification."""

    transactions: list[TransactionInput] = Field(..., min_length=1, max_length=100)


class BatchClassifyResponse(BaseModel):
    """Response model for batch classification."""

    results: list[ClassificationResponse]
    total: int
    needs_review_count: int


class FeedbackRequest(BaseModel):
    """Input model for user feedback/correction."""

    transaction_description: str = Field(..., min_length=1, max_length=500)
    original_category: str
    corrected_category: str
    original_subcategory: Optional[str] = None
    corrected_subcategory: Optional[str] = None
    original_confidence: float = Field(0.0, ge=0.0, le=1.0)
    original_source: str = "unknown"
    amount: Optional[float] = None
    user_note: Optional[str] = Field(None, max_length=200)


class FeedbackResponse(BaseModel):
    """Response after recording feedback."""

    status: str
    message: str


class StatsResponse(BaseModel):
    """Response for classification statistics."""

    pipeline_stats: dict
    feedback_stats: dict


# ─── Endpoints ───────────────────────────────────────────────────────────────


@router.post("", response_model=ClassificationResponse)
def classify_transaction(request: TransactionInput) -> ClassificationResponse:
    """Classify a single transaction.

    Runs through the three-tier pipeline (Rules → ML → LLM) and returns
    the classification with confidence scores.
    """
    pipeline = get_pipeline()

    result = pipeline.classify(
        description=request.description,
        amount=request.amount,
        transaction_type=request.transaction_type,
    )

    return ClassificationResponse(
        category=result.category,
        subcategory=result.subcategory,
        merchant=result.merchant,
        confidence=round(result.confidence, 4),
        confidence_level=result.confidence_level.value,
        source=result.source,
        needs_review=result.needs_review,
        reasoning=result.reasoning,
    )


@router.post("/batch", response_model=BatchClassifyResponse)
def classify_batch(request: BatchClassifyRequest) -> BatchClassifyResponse:
    """Classify multiple transactions in one request.

    More efficient than calling single classification multiple times,
    especially for ML tier which benefits from batching.
    """
    pipeline = get_pipeline()

    transactions = [
        {
            "description": tx.description,
            "amount": tx.amount,
            "transaction_type": tx.transaction_type,
        }
        for tx in request.transactions
    ]

    results = pipeline.classify_batch(transactions)

    responses = [
        ClassificationResponse(
            category=r.category,
            subcategory=r.subcategory,
            merchant=r.merchant,
            confidence=round(r.confidence, 4),
            confidence_level=r.confidence_level.value,
            source=r.source,
            needs_review=r.needs_review,
            reasoning=r.reasoning,
        )
        for r in results
    ]

    needs_review_count = sum(1 for r in results if r.needs_review)

    return BatchClassifyResponse(
        results=responses,
        total=len(responses),
        needs_review_count=needs_review_count,
    )


@router.post("/feedback", response_model=FeedbackResponse)
def submit_feedback(request: FeedbackRequest) -> FeedbackResponse:
    """Submit a user correction for a classification.

    Records the feedback for accuracy tracking and future model improvement.
    """
    store = get_feedback_store()
    pipeline = get_pipeline()

    entry = FeedbackEntry(
        transaction_description=request.transaction_description,
        original_category=request.original_category,
        corrected_category=request.corrected_category,
        original_subcategory=request.original_subcategory,
        corrected_subcategory=request.corrected_subcategory,
        original_confidence=request.original_confidence,
        original_source=request.original_source,
        amount=request.amount,
        user_note=request.user_note,
    )

    store.add_feedback(entry)

    if not entry.was_correct:
        pipeline.record_feedback_correction()

    return FeedbackResponse(
        status="success",
        message=f"Feedback recorded: '{request.corrected_category}' for transaction",
    )


@router.get("/stats", response_model=StatsResponse)
def get_stats() -> StatsResponse:
    """Get classification pipeline performance and accuracy statistics."""
    pipeline = get_pipeline()
    store = get_feedback_store()

    return StatsResponse(
        pipeline_stats=pipeline.stats.to_dict(),
        feedback_stats=store.get_accuracy_stats(),
    )
