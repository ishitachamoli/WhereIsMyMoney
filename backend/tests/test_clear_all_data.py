"""Integration tests for the clear_all_data endpoint."""
import pytest
from datetime import datetime
from tests.conftest import TEST_SESSION_TOKEN


def _headers(session_token=TEST_SESSION_TOKEN):
    return {"Authorization": f"Bearer {session_token}"}


class TestClearAllData:
    """Test the DELETE /api/v1/transactions/data/clear endpoint."""

    def test_clear_all_data_with_classification_jobs(self, client, test_user, db_session):
        """Test clear_all_data with classification jobs (tests FK cascade fix)."""
        from app.models.bank_statement import BankStatement
        from app.models.classification_job import ClassificationJob
        from app.models.transaction import Transaction as TransactionModel

        # Create test data for the user
        stmt = BankStatement(
            user_id=test_user.id,
            filename="test.csv",
            bank_name="Test Bank",
            file_type="csv",
        )
        db_session.add(stmt)
        db_session.commit()
        db_session.refresh(stmt)

        # Create a classification job for this bank statement
        job = ClassificationJob(
            user_id=test_user.id,
            bank_statement_id=stmt.id,
            total_transactions=10,
            classified_transactions=5,
            status="in_progress",
        )
        db_session.add(job)
        db_session.commit()

        # Create a transaction
        txn = TransactionModel(
            user_id=test_user.id,
            bank_statement_id=stmt.id,
            date=datetime.fromisoformat("2024-01-15T10:00:00"),
            description="Test Transaction",
            amount=500.00,
            transaction_type="debit",
        )
        db_session.add(txn)
        db_session.commit()

        # Verify data exists before clear
        assert db_session.query(ClassificationJob).filter(
            ClassificationJob.user_id == test_user.id
        ).count() == 1
        assert db_session.query(TransactionModel).filter(
            TransactionModel.user_id == test_user.id
        ).count() == 1
        assert db_session.query(BankStatement).filter(
            BankStatement.user_id == test_user.id
        ).count() == 1

        # Call clear_all_data endpoint
        response = client.delete(
            "/api/v1/transactions/data/clear",
            headers=_headers(test_user.session_token),
        )
        assert response.status_code == 200

        # Verify response contains correct counts
        data = response.json()
        assert data["deleted_classification_jobs"] == 1
        assert data["deleted_transactions"] == 1
        assert data["deleted_statements"] == 1

        # Verify all data is deleted
        assert db_session.query(ClassificationJob).filter(
            ClassificationJob.user_id == test_user.id
        ).count() == 0
        assert db_session.query(TransactionModel).filter(
            TransactionModel.user_id == test_user.id
        ).count() == 0
        assert db_session.query(BankStatement).filter(
            BankStatement.user_id == test_user.id
        ).count() == 0

    def test_clear_all_data_with_budgets_and_rules(self, client, test_user, db_session):
        """Test clear_all_data deletes budgets and learned rules."""
        from app.models.budget import Budget
        from app.models.learned_rule import LearnedRule
        from app.models.category import Category

        # Create a user-created category
        user_cat = Category(
            user_id=test_user.id,
            name="Custom Food",
            is_system=False,
        )
        db_session.add(user_cat)
        db_session.commit()
        db_session.refresh(user_cat)

        # Create a budget
        budget = Budget(
            user_id=test_user.id,
            category_id=user_cat.id,
            amount=5000.0,
            period="monthly",
        )
        db_session.add(budget)

        # Create a learned rule
        rule = LearnedRule(
            user_id=test_user.id,
            pattern="AMAZON",
            category_name="Shopping",
            confidence=0.95,
        )
        db_session.add(rule)
        db_session.commit()

        # Verify data exists
        assert db_session.query(Budget).filter(Budget.user_id == test_user.id).count() == 1
        assert db_session.query(LearnedRule).filter(
            LearnedRule.user_id == test_user.id
        ).count() == 1
        assert db_session.query(Category).filter(
            Category.user_id == test_user.id,
            Category.is_system == False
        ).count() == 1

        # Call clear_all_data
        response = client.delete(
            "/api/v1/transactions/data/clear",
            headers=_headers(test_user.session_token),
        )
        assert response.status_code == 200
        data = response.json()
        assert data["deleted_budgets"] == 1
        assert data["deleted_learned_rules"] == 1
        assert data["deleted_categories"] == 1

        # Verify all data is deleted
        assert db_session.query(Budget).filter(Budget.user_id == test_user.id).count() == 0
        assert db_session.query(LearnedRule).filter(
            LearnedRule.user_id == test_user.id
        ).count() == 0
        assert db_session.query(Category).filter(
            Category.user_id == test_user.id,
            Category.is_system == False
        ).count() == 0

    def test_clear_all_data_preserves_system_categories(self, client, test_user, db_session):
        """Test that system categories are NOT deleted."""
        from app.models.category import Category

        # Create a system category to verify it's preserved
        system_cat = Category(
            name="System Test Category",
            is_system=True,
        )
        db_session.add(system_cat)
        db_session.commit()

        initial_system_count = db_session.query(Category).filter(
            Category.is_system == True
        ).count()
        assert initial_system_count >= 1

        # Call clear_all_data
        response = client.delete(
            "/api/v1/transactions/data/clear",
            headers=_headers(test_user.session_token),
        )
        assert response.status_code == 200

        # System categories should still exist
        final_system_count = db_session.query(Category).filter(
            Category.is_system == True
        ).count()
        assert final_system_count == initial_system_count

    def test_clear_all_data_empty_user(self, client, test_user):
        """Test clear_all_data with user that has no data."""
        response = client.delete(
            "/api/v1/transactions/data/clear",
            headers=_headers(test_user.session_token),
        )
        assert response.status_code == 200
        data = response.json()
        assert data["deleted_classification_jobs"] == 0
        assert data["deleted_learned_rules"] == 0
        assert data["deleted_budgets"] == 0
        assert data["deleted_categories"] == 0
        assert data["deleted_transactions"] == 0
        assert data["deleted_statements"] == 0
