"""Test auto-migration of database columns."""
import os
import tempfile
import pytest
from sqlalchemy import create_engine, inspect, Column, Integer, String, Float
from sqlalchemy.orm import sessionmaker, DeclarativeBase
from sqlalchemy.sql import func
from datetime import datetime

from app.core.database import Base, auto_migrate_columns
from app.models import Transaction, User, Category
from app.models.transaction import TransactionType


class OldBase(DeclarativeBase):
    """Old schema without the new columns (simulates old database state)."""
    pass


class OldTransaction(OldBase):
    """Old Transaction model without source, confidence_score, classification_source."""
    __tablename__ = "transactions"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, index=True, nullable=False)
    bank_statement_id = Column(Integer, nullable=True)
    category_id = Column(Integer, nullable=True, index=True)
    date = Column(Integer, nullable=False, index=True)  # Simplified for test
    description = Column(String, nullable=False)
    amount = Column(Float, nullable=False)
    transaction_type = Column(String, nullable=False)
    balance = Column(Float, nullable=True)
    reference_number = Column(String(100), nullable=True)
    bank_name = Column(String(50), nullable=True)
    account_number = Column(String(50), nullable=True)
    created_at = Column(Integer)  # Simplified for test
    updated_at = Column(Integer)


@pytest.fixture
def temp_sqlite_db():
    """Create a temporary SQLite database for testing."""
    fd, db_path = tempfile.mkstemp(suffix=".db")
    os.close(fd)
    yield f"sqlite:///{db_path}"
    # Cleanup
    if os.path.exists(db_path):
        os.remove(db_path)


def test_auto_migrate_adds_missing_columns(temp_sqlite_db):
    """Test that auto_migrate_columns adds missing columns to existing tables."""
    # Step 1: Create database with old schema
    old_engine = create_engine(temp_sqlite_db)
    OldBase.metadata.create_all(bind=old_engine)

    # Verify old schema has only the old columns
    inspector = inspect(old_engine)
    old_columns = {col["name"] for col in inspector.get_columns("transactions")}
    assert "source" not in old_columns
    assert "confidence_score" not in old_columns
    assert "classification_source" not in old_columns
    old_engine.dispose()

    # Step 2: Create new engine and run auto-migration with new schema
    new_engine = create_engine(temp_sqlite_db)
    
    # Create all base models first (user, category, etc.)
    Base.metadata.create_all(bind=new_engine)
    
    # Now run auto_migrate_columns to add missing columns
    auto_migrate_columns(new_engine)

    # Step 3: Verify new columns were added
    inspector = inspect(new_engine)
    new_columns = {col["name"] for col in inspector.get_columns("transactions")}
    
    assert "source" in new_columns, "source column should be added"
    assert "confidence_score" in new_columns, "confidence_score column should be added"
    assert "classification_source" in new_columns, "classification_source column should be added"
    
    # Verify the columns have correct properties
    columns_info = {col["name"]: col for col in inspector.get_columns("transactions")}
    
    # source should be VARCHAR(20) NOT NULL DEFAULT 'upload'
    assert columns_info["source"]["nullable"] is False or columns_info["source"]["default"] is not None
    
    # confidence_score should be FLOAT NOT NULL DEFAULT 1.0
    assert columns_info["confidence_score"]["nullable"] is False or columns_info["confidence_score"]["default"] is not None
    
    # classification_source should be VARCHAR(30) NOT NULL DEFAULT 'rule'
    assert columns_info["classification_source"]["nullable"] is False or columns_info["classification_source"]["default"] is not None
    
    new_engine.dispose()


def test_auto_migrate_handles_missing_tables(temp_sqlite_db):
    """Test that auto_migrate_columns gracefully handles tables that don't exist yet."""
    # Create engine without any tables
    engine = create_engine(temp_sqlite_db)
    
    # This should not raise an error even though tables don't exist
    auto_migrate_columns(engine)
    
    # Now create tables normally
    Base.metadata.create_all(bind=engine)
    
    # Verify tables were created
    inspector = inspect(engine)
    assert inspector.has_table("transactions")
    assert inspector.has_table("users")
    
    engine.dispose()


def test_auto_migrate_with_multiple_tables(temp_sqlite_db):
    """Test that auto_migrate_columns works with multiple tables."""
    # Create old database
    old_engine = create_engine(temp_sqlite_db)
    OldBase.metadata.create_all(bind=old_engine)
    
    # Create users table (this is not in OldBase, so it won't be created yet)
    # But we'll add it to test the multi-table scenario
    old_engine.dispose()
    
    # Run auto-migration with full new schema
    new_engine = create_engine(temp_sqlite_db)
    Base.metadata.create_all(bind=new_engine)
    auto_migrate_columns(new_engine)
    
    # Verify all tables exist and have the right columns
    inspector = inspect(new_engine)
    
    # Check transactions table
    trans_cols = {col["name"] for col in inspector.get_columns("transactions")}
    assert "source" in trans_cols
    assert "confidence_score" in trans_cols
    assert "classification_source" in trans_cols
    
    # Check users table exists
    assert inspector.has_table("users")
    
    new_engine.dispose()


def test_auto_migrate_idempotent(temp_sqlite_db):
    """Test that running auto_migrate_columns multiple times is safe (idempotent)."""
    # Create database
    engine = create_engine(temp_sqlite_db)
    Base.metadata.create_all(bind=engine)
    
    # Run auto_migrate twice
    auto_migrate_columns(engine)
    auto_migrate_columns(engine)  # Should not fail
    
    # Verify columns exist and are correct
    inspector = inspect(engine)
    cols = {col["name"] for col in inspector.get_columns("transactions")}
    
    assert "source" in cols
    assert "confidence_score" in cols
    assert "classification_source" in cols
    
    engine.dispose()


def test_auto_migrate_preserves_existing_data(temp_sqlite_db):
    """Test that auto_migrate_columns doesn't lose existing data when adding columns."""
    # Create old database and add some data
    old_engine = create_engine(temp_sqlite_db)
    OldBase.metadata.create_all(bind=old_engine)
    
    # Insert a transaction
    OldSessionLocal = sessionmaker(bind=old_engine)
    session = OldSessionLocal()
    session.execute(
        OldBase.metadata.tables["transactions"].insert().values(
            user_id=1,
            description="Test transaction",
            amount=100.0,
            transaction_type="debit",
            date=1234567890
        )
    )
    session.commit()
    session.close()
    old_engine.dispose()
    
    # Run auto-migration
    new_engine = create_engine(temp_sqlite_db)
    Base.metadata.create_all(bind=new_engine)
    auto_migrate_columns(new_engine)
    
    # Verify the data is still there
    NewSessionLocal = sessionmaker(bind=new_engine)
    session = NewSessionLocal()
    
    # Query the transaction - this tests that schema is still valid
    from sqlalchemy import text
    result = session.execute(text("SELECT COUNT(*) FROM transactions"))
    count = result.scalar()
    assert count == 1
    
    session.close()
    new_engine.dispose()
