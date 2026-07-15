"""Integration tests for analytics endpoints."""
import pytest
from tests.conftest import get_fixture_path, TEST_SESSION_TOKEN


def _headers():
    return {"Authorization": f"Bearer {TEST_SESSION_TOKEN}"}


class TestAnalyticsEndpoints:
    """Test the /api/v1/analytics endpoints."""

    def _upload_fixture(self, client, fixture_name):
        """Helper to upload a bank statement fixture."""
        filepath = get_fixture_path(fixture_name)
        with open(filepath, "rb") as f:
            return client.post(
                "/api/v1/upload",
                files={"file": (fixture_name, f, "text/csv")},
                headers=_headers(),
            )

    def test_spending_by_category_empty(self, client, test_user):
        """Empty spending when no transactions."""
        response = client.get(
            "/api/v1/analytics/spending-by-category",
            headers=_headers(),
        )
        assert response.status_code == 200
        assert response.json() == []

    def test_spending_by_category_with_data(self, client, test_user, test_categories):
        """Spending by category after uploading transactions."""
        self._upload_fixture(client, "hdfc_statement.csv")

        response = client.get(
            "/api/v1/analytics/spending-by-category",
            headers=_headers(),
        )
        assert response.status_code == 200
        data = response.json()

        assert len(data) >= 1
        total = sum(item["total_amount"] for item in data)
        assert total > 0

        total_pct = sum(item["percentage"] for item in data)
        assert abs(total_pct - 100.0) < 0.1

    def test_timeline_monthly(self, client, test_user):
        """Monthly timeline data."""
        self._upload_fixture(client, "hdfc_statement.csv")

        response = client.get(
            "/api/v1/analytics/timeline",
            params={"granularity": "monthly"},
            headers=_headers(),
        )
        assert response.status_code == 200
        data = response.json()

        assert len(data) >= 1
        entry = data[0]
        assert "period" in entry
        assert "total_credits" in entry
        assert "total_debits" in entry
        assert "net" in entry
        assert "transaction_count" in entry

    def test_timeline_daily(self, client, test_user):
        """Daily timeline data."""
        self._upload_fixture(client, "hdfc_statement.csv")

        response = client.get(
            "/api/v1/analytics/timeline",
            params={"granularity": "daily"},
            headers=_headers(),
        )
        assert response.status_code == 200
        data = response.json()
        assert len(data) >= 1
        assert len(data[0]["period"]) == 10

    def test_income_vs_expenses(self, client, test_user):
        """Income vs expenses summary."""
        self._upload_fixture(client, "hdfc_statement.csv")

        response = client.get(
            "/api/v1/analytics/income-vs-expenses",
            headers=_headers(),
        )
        assert response.status_code == 200
        data = response.json()
        assert isinstance(data, list)
        assert len(data) >= 1

    def test_income_vs_expenses_empty(self, client, test_user):
        """Income vs expenses with no data."""
        response = client.get(
            "/api/v1/analytics/income-vs-expenses",
            headers=_headers(),
        )
        assert response.status_code == 200
        data = response.json()
        assert isinstance(data, list)

    def test_analytics_summary(self, client, test_user):
        """Full analytics summary endpoint."""
        self._upload_fixture(client, "hdfc_statement.csv")

        response = client.get(
            "/api/v1/analytics/summary",
            headers=_headers(),
        )
        assert response.status_code == 200
        data = response.json()

        assert "total_income" in data
        assert "total_expenses" in data

    def test_analytics_with_date_range(self, client, test_user):
        """Analytics filtered by date range."""
        self._upload_fixture(client, "hdfc_statement.csv")

        response = client.get(
            "/api/v1/analytics/spending-by-category",
            params={
                "start_date": "2024-01-01T00:00:00",
                "end_date": "2024-01-15T23:59:59",
            },
            headers=_headers(),
        )
        assert response.status_code == 200
        data = response.json()
        assert isinstance(data, list)

    def test_multiple_uploads_aggregated(self, client, test_user):
        """Analytics aggregate transactions from multiple uploads."""
        self._upload_fixture(client, "hdfc_statement.csv")
        self._upload_fixture(client, "icici_statement.csv")

        response = client.get(
            "/api/v1/analytics/income-vs-expenses",
            headers=_headers(),
        )
        assert response.status_code == 200
        data = response.json()
        assert isinstance(data, list)

    def test_unauthorized_access(self, client, test_user):
        """Verify 401 without auth."""
        response = client.get("/api/v1/analytics/summary")
        assert response.status_code == 401
