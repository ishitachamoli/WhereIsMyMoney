from pydantic import BaseModel, Field
from datetime import datetime
from typing import Optional, Literal
from app.models.transaction import TransactionType


class TransactionBase(BaseModel):
    date: datetime
    description: str
    amount: float = Field(..., gt=0)
    transaction_type: TransactionType
    balance: Optional[float] = None
    reference_number: Optional[str] = None
    bank_name: Optional[str] = None
    account_number: Optional[str] = None
    category_id: Optional[int] = None
    source: Literal["upload", "manual"] = "upload"


class TransactionCreate(TransactionBase):
    user_id: int


class ManualTransactionCreate(BaseModel):
    """Simplified schema for manually creating a cash transaction."""
    description: str = Field(..., min_length=1)
    amount: float = Field(..., description="Positive = expense amount, negative allowed for explicit sign")
    transaction_date: Optional[str] = None
    transaction_type: TransactionType = TransactionType.DEBIT
    category_name: Optional[str] = None
    source: Literal["upload", "manual"] = "manual"


class TransactionUpdate(BaseModel):
    date: Optional[datetime] = None
    description: Optional[str] = None
    amount: Optional[float] = Field(None, gt=0)
    transaction_type: Optional[TransactionType] = None
    balance: Optional[float] = None
    reference_number: Optional[str] = None
    category_id: Optional[int] = None
    category_name: Optional[str] = None


class TransactionResponse(BaseModel):
    """Matches frontend Transaction type."""
    model_config = {"from_attributes": True}

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
    source: str = "upload"
    currency: str = "INR"
    tags: Optional[list[str]] = None
    is_recurring: bool
    notes: Optional[str] = None
    metadata: Optional[dict] = None
    created_at: str
    updated_at: str


class TotalsResponse(BaseModel):
    """Aggregated amounts for the entire filtered transaction set.

    These totals reflect ALL transactions matching the active filters
    (category, type, date range, search, etc.) — NOT just the current page.
    All amounts are positive; ``net_amount`` is ``credit_amount - debit_amount``.

    Attributes:
        credit_amount: Sum of all credit/income amounts in the filtered set.
        debit_amount: Sum of all debit/expense amounts in the filtered set.
        net_amount: ``credit_amount - debit_amount`` (may be negative).
        currency: Dominant currency code for the user (e.g. ``"EUR"``, ``"INR"``).
    """
    credit_amount: float = 0.0
    debit_amount: float = 0.0
    net_amount: float = 0.0
    currency: str = "INR"


class TransactionListResponse(BaseModel):
    """Matches frontend PaginatedResponse<Transaction> type."""
    items: list[TransactionResponse]
    total: int
    page: int
    page_size: int
    total_pages: int
    totals: Optional[TotalsResponse] = None
