from sqlalchemy import Column, Integer, String, Float, DateTime, ForeignKey, Enum as SQLEnum, Text
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
from app.core.database import Base
import enum


class TransactionType(str, enum.Enum):
    DEBIT = "debit"
    CREDIT = "credit"


class Transaction(Base):
    __tablename__ = "transactions"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False, index=True)
    bank_statement_id = Column(Integer, ForeignKey("bank_statements.id"), nullable=True)
    category_id = Column(Integer, ForeignKey("categories.id"), nullable=True, index=True)

    date = Column(DateTime(timezone=True), nullable=False, index=True)
    description = Column(Text, nullable=False)
    amount = Column(Float, nullable=False)
    transaction_type = Column(SQLEnum(TransactionType), nullable=False)
    balance = Column(Float, nullable=True)
    reference_number = Column(String(100), nullable=True)
    bank_name = Column(String(50), nullable=True)
    account_number = Column(String(50), nullable=True)
    currency = Column(String(10), nullable=False, default="INR", server_default="INR")

    source = Column(String(20), nullable=False, default="upload", server_default="upload")

    confidence_score = Column(Float, nullable=False, default=1.0, server_default="1.0")
    classification_source = Column(String(30), nullable=False, default="rule", server_default="rule")

    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())

    user = relationship("User", back_populates="transactions")
    bank_statement = relationship("BankStatement", back_populates="transactions")
    category = relationship("Category", back_populates="transactions")
