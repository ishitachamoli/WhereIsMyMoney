"""Classification job model for tracking background ML classification progress."""
import uuid

from sqlalchemy import Column, Integer, String, DateTime, ForeignKey
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func

from app.core.database import Base


def generate_uuid() -> str:
    return str(uuid.uuid4())


class ClassificationJob(Base):
    __tablename__ = "classification_jobs"

    id = Column(String(36), primary_key=True, default=generate_uuid)
    user_id = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)
    bank_statement_id = Column(Integer, ForeignKey("bank_statements.id", ondelete="CASCADE"), nullable=True)
    total_transactions = Column(Integer, nullable=False, default=0)
    classified_transactions = Column(Integer, nullable=False, default=0)
    status = Column(String(20), nullable=False, default="pending")
    started_at = Column(DateTime(timezone=True), server_default=func.now())
    completed_at = Column(DateTime(timezone=True), nullable=True)
    error = Column(String(500), nullable=True)

    user = relationship("User")
    bank_statement = relationship("BankStatement")
