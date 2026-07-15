"""Integration tests for transaction CRUD endpoints."""
import pytest
from datetime import datetime
from tests.conftest import TEST_SESSION_TOKEN


def _headers():
    return {"Authorization": f"Bearer {TEST_SESSION_TOKEN}"}


class TestTransactionCRUD:
    """Test the /api/v1/transactions endpoint."""

    def _create_transaction(self, client, **kwargs):
        """Helper to create a transaction."""
        data = {
            "user_id": 1,
            "date": "2024-01-15T10:00:00",
            "description": "Test Transaction",
            "amount": 500.00,
            "transaction_type": "debit",
            **kwargs,
        }
        return client.post("/api/v1/transactions", json=data, headers=_headers())

    def test_create_transaction(self, client, test_user):
        """Create a transaction and verify response."""
        response = self._create_transaction(client)
        assert response.status_code == 201

        data = response.json()
        assert data["description"] == "Test Transaction"
        assert data["amount"] == 500.00
        assert data["transaction_type"] == "debit"
        assert data["id"] is not None

    def test_create_credit_transaction(self, client, test_user):
        """Create a credit transaction."""
        response = self._create_transaction(
            client,
            description="Salary Credit",
            amount=75000.00,
            transaction_type="credit",
        )
        assert response.status_code == 201
        assert response.json()["transaction_type"] == "credit"
        assert response.json()["amount"] == 75000.00

    def test_get_transaction(self, client, test_user):
        """Get a single transaction by ID."""
        create_resp = self._create_transaction(client)
        txn_id = create_resp.json()["id"]

        response = client.get(f"/api/v1/transactions/{txn_id}", headers=_headers())
        assert response.status_code == 200
        assert response.json()["id"] == txn_id

    def test_get_transaction_not_found(self, client, test_user):
        """404 for non-existent transaction."""
        response = client.get("/api/v1/transactions/9999", headers=_headers())
        assert response.status_code == 404

    def test_list_transactions(self, client, test_user):
        """List transactions with pagination."""
        for i in range(5):
            self._create_transaction(
                client,
                description=f"Transaction {i}",
                amount=100.0 * (i + 1),
            )

        response = client.get("/api/v1/transactions", headers=_headers())
        assert response.status_code == 200
        data = response.json()
        assert data["total"] == 5
        assert len(data["items"]) == 5
        assert data["page"] == 1

    def test_list_transactions_pagination(self, client, test_user):
        """Test pagination."""
        for i in range(10):
            self._create_transaction(
                client,
                description=f"Transaction {i}",
                amount=100.0,
            )

        response = client.get(
            "/api/v1/transactions",
            params={"page": 1, "page_size": 3},
            headers=_headers(),
        )
        assert response.status_code == 200
        data = response.json()
        assert data["total"] == 10
        assert len(data["items"]) == 3
        assert data["page_size"] == 3

    def test_list_transactions_filter_by_type(self, client, test_user):
        """Filter by transaction type."""
        self._create_transaction(client, transaction_type="debit", amount=100)
        self._create_transaction(client, transaction_type="credit", amount=200)

        response = client.get(
            "/api/v1/transactions",
            params={"transaction_type": "credit"},
            headers=_headers(),
        )
        assert response.status_code == 200
        data = response.json()
        assert data["total"] == 1
        assert data["items"][0]["transaction_type"] == "credit"

    def test_list_transactions_search(self, client, test_user):
        """Search by description."""
        self._create_transaction(client, description="SWIGGY FOOD ORDER")
        self._create_transaction(client, description="SALARY CREDIT")

        response = client.get(
            "/api/v1/transactions",
            params={"search": "SWIGGY"},
            headers=_headers(),
        )
        assert response.status_code == 200
        data = response.json()
        assert data["total"] == 1
        assert "SWIGGY" in data["items"][0]["description"]

    def test_update_transaction(self, client, test_user):
        """Update a transaction's description and category."""
        create_resp = self._create_transaction(client)
        txn_id = create_resp.json()["id"]

        response = client.put(
            f"/api/v1/transactions/{txn_id}",
            json={"description": "Updated Description", "amount": 750.00},
            headers=_headers(),
        )
        assert response.status_code == 200
        data = response.json()
        assert data["description"] == "Updated Description"
        assert data["amount"] == 750.00

    def test_update_transaction_not_found(self, client, test_user):
        """404 when updating non-existent transaction."""
        response = client.put(
            "/api/v1/transactions/9999",
            json={"description": "Updated"},
            headers=_headers(),
        )
        assert response.status_code == 404

    def test_delete_transaction(self, client, test_user):
        """Delete a transaction."""
        create_resp = self._create_transaction(client)
        txn_id = create_resp.json()["id"]

        response = client.delete(f"/api/v1/transactions/{txn_id}", headers=_headers())
        assert response.status_code == 204

        # Verify deletion
        get_resp = client.get(f"/api/v1/transactions/{txn_id}", headers=_headers())
        assert get_resp.status_code == 404

    def test_delete_transaction_not_found(self, client, test_user):
        """404 when deleting non-existent transaction."""
        response = client.delete("/api/v1/transactions/9999", headers=_headers())
        assert response.status_code == 404

    def test_unauthorized_access(self, client, test_user):
        """Verify 401 without auth."""
        response = client.get("/api/v1/transactions")
        assert response.status_code == 401


class TestTransactionTotals:
    """Test the filtered totals aggregate on the list endpoint."""

    def _create(self, client, date=None, **kwargs):
        data = {
            "description": "Test Transaction",
            "amount": 500.00,
            "transaction_type": "debit",
            **kwargs,
        }
        if date is not None:
            data["transaction_date"] = date
        return client.post("/api/v1/transactions", json=data, headers=_headers())

    def test_totals_no_filters(self, client, test_user):
        """Totals match the sum of all transactions when no filters applied."""
        self._create(client, transaction_type="credit", amount=1000.0)
        self._create(client, transaction_type="credit", amount=500.0)
        self._create(client, transaction_type="debit", amount=300.0)

        resp = client.get("/api/v1/transactions", headers=_headers())
        assert resp.status_code == 200
        totals = resp.json()["totals"]
        assert totals["credit_amount"] == 1500.0
        assert totals["debit_amount"] == 300.0
        assert totals["net_amount"] == 1200.0
        assert totals["currency"] == "INR"

    def test_totals_ignore_pagination(self, client, test_user):
        """Totals reflect the entire filtered set, not just the current page."""
        for _ in range(5):
            self._create(client, transaction_type="debit", amount=100.0)

        resp = client.get(
            "/api/v1/transactions",
            params={"page": 1, "page_size": 2},
            headers=_headers(),
        )
        assert resp.status_code == 200
        body = resp.json()
        assert len(body["items"]) == 2
        assert body["totals"]["debit_amount"] == 500.0

    def test_totals_category_filter(self, client, test_user, test_categories):
        """Totals reflect only the filtered category's rows."""
        self._create(client, category_name="Food & Dining", amount=200.0, transaction_type="debit")
        self._create(client, category_name="Food & Dining", amount=300.0, transaction_type="debit")
        self._create(client, category_name="Shopping", amount=999.0, transaction_type="debit")

        resp = client.get(
            "/api/v1/transactions",
            params={"category": "Food & Dining"},
            headers=_headers(),
        )
        assert resp.status_code == 200
        totals = resp.json()["totals"]
        assert totals["debit_amount"] == 500.0
        assert totals["credit_amount"] == 0.0

    def test_totals_date_range_filter(self, client, test_user):
        """Totals reflect only transactions in the date range."""
        self._create(client, date="2024-03-10T10:00:00", amount=100.0, transaction_type="debit")
        self._create(client, date="2024-03-20T10:00:00", amount=250.0, transaction_type="debit")
        self._create(client, date="2024-05-01T10:00:00", amount=999.0, transaction_type="debit")

        resp = client.get(
            "/api/v1/transactions",
            params={"start_date": "2024-03-01T00:00:00", "end_date": "2024-03-31T23:59:59"},
            headers=_headers(),
        )
        assert resp.status_code == 200
        totals = resp.json()["totals"]
        assert totals["debit_amount"] == 350.0

    def test_totals_type_filter_credit_only(self, client, test_user):
        """When filtering credit-only, debit_amount is 0."""
        self._create(client, transaction_type="credit", amount=800.0)
        self._create(client, transaction_type="debit", amount=400.0)

        resp = client.get(
            "/api/v1/transactions",
            params={"transaction_type": "credit"},
            headers=_headers(),
        )
        assert resp.status_code == 200
        totals = resp.json()["totals"]
        assert totals["credit_amount"] == 800.0
        assert totals["debit_amount"] == 0.0
        assert totals["net_amount"] == 800.0

    def test_totals_empty_result(self, client, test_user):
        """Empty result set returns all-zero totals with default currency."""
        resp = client.get(
            "/api/v1/transactions",
            params={"search": "NONEXISTENT_XYZ"},
            headers=_headers(),
        )
        assert resp.status_code == 200
        totals = resp.json()["totals"]
        assert totals["credit_amount"] == 0.0
        assert totals["debit_amount"] == 0.0
        assert totals["net_amount"] == 0.0
        assert totals["currency"] == "INR"

    def test_totals_multi_filter_combo(self, client, test_user, test_categories):
        """Category + date range + search combine to produce correct totals."""
        self._create(
            client, category_name="Food & Dining", date="2024-03-05T10:00:00",
            description="SWIGGY ORDER", amount=150.0, transaction_type="debit",
        )
        self._create(
            client, category_name="Food & Dining", date="2024-03-25T10:00:00",
            description="SWIGGY DINNER", amount=250.0, transaction_type="debit",
        )
        # Same category+search but outside date range
        self._create(
            client, category_name="Food & Dining", date="2024-06-01T10:00:00",
            description="SWIGGY LUNCH", amount=999.0, transaction_type="debit",
        )
        # Same category+date but different search
        self._create(
            client, category_name="Food & Dining", date="2024-03-15T10:00:00",
            description="ZOMATO ORDER", amount=888.0, transaction_type="debit",
        )

        resp = client.get(
            "/api/v1/transactions",
            params={
                "category": "Food & Dining",
                "start_date": "2024-03-01T00:00:00",
                "end_date": "2024-03-31T23:59:59",
                "search": "SWIGGY",
            },
            headers=_headers(),
        )
        assert resp.status_code == 200
        totals = resp.json()["totals"]
        assert totals["debit_amount"] == 400.0
        assert totals["credit_amount"] == 0.0
