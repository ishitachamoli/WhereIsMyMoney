"""Integration test for auto-migration during app startup."""
import os
import tempfile
import pytest
from sqlalchemy import create_engine, inspect, text
from sqlalchemy.orm import sessionmaker

from app.core.database import Base, auto_migrate_columns


def test_app_startup_migration_flow():
    """
    Integration test: simulate the actual app startup flow with auto-migration.
    
    This test verifies the real scenario:
    1. Old database exists with missing columns
    2. App starts up and runs auto_migrate_columns
    3. New columns are added
    4. App can then use create_all without issues
    """
    # Create a temporary database file
    fd, db_path = tempfile.mkstemp(suffix=".db")
    os.close(fd)
    db_url = f"sqlite:///{db_path}"
    
    try:
        # Step 1: Simulate old database state by creating tables without new columns
        old_engine = create_engine(db_url)
        
        # Create an old version of transactions table without the new columns
        with old_engine.connect() as conn:
            conn.execute(text("""
                CREATE TABLE transactions (
                    id INTEGER PRIMARY KEY,
                    user_id INTEGER NOT NULL,
                    bank_statement_id INTEGER,
                    category_id INTEGER,
                    date DATETIME NOT NULL,
                    description TEXT NOT NULL,
                    amount FLOAT NOT NULL,
                    transaction_type VARCHAR NOT NULL,
                    balance FLOAT,
                    reference_number VARCHAR(100),
                    bank_name VARCHAR(50),
                    account_number VARCHAR(50),
                    created_at DATETIME,
                    updated_at DATETIME
                )
            """))
            conn.commit()
        
        old_engine.dispose()
        
        # Verify old schema has no new columns
        inspector = inspect(old_engine)
        old_columns = {col["name"] for col in inspector.get_columns("transactions")}
        assert "source" not in old_columns
        assert "confidence_score" not in old_columns
        assert "classification_source" not in old_columns
        print("✓ Old database state verified (missing new columns)")
        
        # Step 2: Startup sequence - auto-migrate first, then create_all
        engine = create_engine(db_url)
        
        # This is what _init_database does:
        auto_migrate_columns(engine)  # Adds missing columns
        Base.metadata.create_all(bind=engine)  # Creates any new tables
        
        print("✓ Auto-migration and create_all completed")
        
        # Step 3: Verify new columns exist
        inspector = inspect(engine)
        new_columns = {col["name"] for col in inspector.get_columns("transactions")}
        
        assert "source" in new_columns
        assert "confidence_score" in new_columns
        assert "classification_source" in new_columns
        print("✓ All new columns added successfully")
        
        # Step 4: Verify we can insert and query without issues
        SessionLocal = sessionmaker(bind=engine)
        session = SessionLocal()
        
        # Insert a test transaction with the new columns
        session.execute(
            text("""
                INSERT INTO transactions 
                (user_id, description, amount, transaction_type, date, source, confidence_score, classification_source)
                VALUES 
                (:user_id, :desc, :amt, :type, :date, :source, :score, :class_src)
            """),
            {
                "user_id": 1,
                "desc": "Test transaction",
                "amt": 100.0,
                "type": "debit",
                "date": "2024-01-01 10:00:00",
                "source": "upload",
                "score": 0.95,
                "class_src": "rule",
            }
        )
        session.commit()
        
        # Query it back
        result = session.execute(
            text("SELECT source, confidence_score, classification_source FROM transactions WHERE id = 1")
        )
        row = result.fetchone()
        
        assert row[0] == "upload"  # source
        assert row[1] == 0.95  # confidence_score
        assert row[2] == "rule"  # classification_source
        print("✓ Insert and query with new columns works")
        
        session.close()
        
        print("\n✅ Integration test passed: Auto-migration flow works end-to-end")
        
    finally:
        # Cleanup
        if os.path.exists(db_path):
            os.remove(db_path)


if __name__ == "__main__":
    test_app_startup_migration_flow()
