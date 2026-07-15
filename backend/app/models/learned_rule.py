"""User-learned classification rules from corrections."""
from sqlalchemy import Column, Integer, String, Float, DateTime, ForeignKey
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
from app.core.database import Base


class LearnedRule(Base):
    __tablename__ = "learned_rules"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)
    pattern = Column(String(255), nullable=False, index=True)
    category_name = Column(String(100), nullable=False)
    confidence = Column(Float, nullable=False, default=1.0, server_default="1.0")
    hit_count = Column(Integer, nullable=False, default=1, server_default="1")
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())

    user = relationship("User", back_populates="learned_rules")
