from pydantic import BaseModel
from datetime import datetime
from typing import Optional


class BankStatementResponse(BaseModel):
    model_config = {"from_attributes": True}

    id: int
    user_id: int
    filename: str
    bank_name: str
    file_type: str
    upload_date: datetime
    start_date: Optional[datetime] = None
    end_date: Optional[datetime] = None
    transaction_count: int
    total_credits: float
    total_debits: float


class UploadSummary(BaseModel):
    total_transactions: int
    date_range: dict  # {"start": str, "end": str}
    total_income: float
    total_expenses: float
    net_cash_flow: float
    categories_detected: int
    transactions_needing_review: int
    processing_time_seconds: float


class TransactionResponse(BaseModel):
    id: int
    account_id: int
    transaction_date: str
    description: str
    amount: float
    transaction_type: str
    balance: Optional[float] = None
    reference_number: Optional[str] = None
    merchant_name: Optional[str] = None
    category: str
    subcategory: Optional[str] = None
    confidence_score: float
    classification_tier: str
    currency: str = "INR"
    tags: Optional[list[str]] = None
    is_recurring: bool
    notes: Optional[str] = None
    metadata: Optional[dict] = None
    created_at: str
    updated_at: str


class CategoryBreakdownResponse(BaseModel):
    category: str
    total_amount: float
    percentage: float
    transaction_count: int
    average_transaction: float


class UploadResponse(BaseModel):
    upload_id: int
    status: str
    summary: UploadSummary
    transactions: list[TransactionResponse]
    category_breakdown: list[CategoryBreakdownResponse]
    warnings: Optional[list[str]] = None
    classification_job_id: Optional[str] = None
