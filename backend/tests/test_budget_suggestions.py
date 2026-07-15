"""Integration tests for smart AI-driven budget suggestions."""
import pytest
from datetime import datetime, timedelta
from tests.conftest import TEST_SESSION_TOKEN


def _headers():
    return {"Authorization": f"Bearer {TEST_SESSION_TOKEN}"}


class TestBudgetSuggestions:
    """Test the /api/v1/budgets/suggest endpoint with smart AI analysis."""

    def _create_tx(self, client, date, amount, category_name=None, tx_type="debit"):
        """Helper to create a transaction using the actual API schema."""
        data = {
            "description": "Test Transaction",
            "amount": amount,
            "transaction_type": tx_type,
            "transaction_date": date.isoformat() if hasattr(date, 'isoformat') else date,
        }
        if category_name:
            data["category_name"] = category_name
        resp = client.post("/api/v1/transactions", json=data, headers=_headers())
        assert resp.status_code == 201, f"Failed to create tx: {resp.json()}"
        return resp

    def test_suggest_budgets_with_no_transactions(self, client, test_user):
        """Suggest budgets with no transaction history - should return empty list."""
        response = client.get("/api/v1/budgets/suggest", headers=_headers())
        assert response.status_code == 200
        data = response.json()
        assert data["suggestions"] == []

    def test_suggest_budgets_returns_new_schema_fields(self, client, test_user, test_categories):
        """Verify the response includes all new smart fields."""
        base_date = datetime(2025, 1, 15)
        for month in range(6):
            self._create_tx(
                client,
                base_date + timedelta(days=month * 30),
                1000 + month * 50,
                category_name="Food & Dining",
            )

        response = client.get("/api/v1/budgets/suggest", headers=_headers())
        assert response.status_code == 200
        data = response.json()

        assert len(data["suggestions"]) > 0
        s = data["suggestions"][0]

        # Verify all new schema fields exist
        assert "category_name" in s
        assert "suggested_amount" in s
        assert "confidence" in s
        assert "rationale" in s
        assert "methodology" in s
        assert "avg_monthly_spend" in s
        assert "trend" in s
        assert "months_analyzed" in s
        # Backwards-compatible fields
        assert "average_spending" in s
        assert "reasoning" in s

        # Validate field values
        assert 0 <= s["confidence"] <= 1
        assert s["trend"] in ("increasing", "decreasing", "stable")
        assert s["methodology"] in (
            "trend_projection", "median_with_buffer",
            "fifty_thirty_twenty", "consistency_based"
        )
        assert s["months_analyzed"] >= 1
        assert s["avg_monthly_spend"] > 0
        assert s["suggested_amount"] > 0
        assert len(s["rationale"]) > 10

    def test_suggest_budgets_with_consistent_spending(self, client, test_user, test_categories):
        """Consistent spending should use consistency_based methodology with tight buffer."""
        base_date = datetime(2025, 1, 15)
        amounts = [1000, 1010, 990, 1005, 995, 1000]
        for i, amt in enumerate(amounts):
            self._create_tx(
                client,
                base_date + timedelta(days=i * 30),
                amt,
                category_name="Food & Dining",
            )

        response = client.get("/api/v1/budgets/suggest", headers=_headers())
        assert response.status_code == 200
        data = response.json()

        food_sugg = next((s for s in data["suggestions"] if s["category_name"] == "Food & Dining"), None)
        assert food_sugg is not None, f"No Food & Dining suggestion found. Got: {[s['category_name'] for s in data['suggestions']]}"
        assert food_sugg["methodology"] == "consistency_based"
        assert food_sugg["trend"] == "stable"
        assert food_sugg["suggested_amount"] <= 1200
        assert food_sugg["confidence"] >= 0.8

    def test_suggest_budgets_detects_increasing_trend(self, client, test_user, test_categories):
        """Increasing spending should use trend_projection methodology."""
        base_date = datetime(2025, 1, 15)
        amounts = [500, 700, 900, 1100, 1300, 1500]
        for i, amt in enumerate(amounts):
            self._create_tx(
                client,
                base_date + timedelta(days=i * 30),
                amt,
                category_name="Food & Dining",
            )

        response = client.get("/api/v1/budgets/suggest", headers=_headers())
        assert response.status_code == 200
        data = response.json()

        food_sugg = next((s for s in data["suggestions"] if s["category_name"] == "Food & Dining"), None)
        assert food_sugg is not None, f"No Food & Dining suggestion. Got: {[s['category_name'] for s in data['suggestions']]}"
        assert food_sugg["trend"] == "increasing"
        assert food_sugg["methodology"] == "trend_projection"
        assert food_sugg["suggested_amount"] >= 1400

    def test_suggest_budgets_detects_decreasing_trend(self, client, test_user, test_categories):
        """Decreasing spending should reward with buffer on projected value."""
        base_date = datetime(2025, 1, 15)
        amounts = [2000, 1700, 1400, 1100, 800, 500]
        for i, amt in enumerate(amounts):
            self._create_tx(
                client,
                base_date + timedelta(days=i * 30),
                amt,
                category_name="Food & Dining",
            )

        response = client.get("/api/v1/budgets/suggest", headers=_headers())
        assert response.status_code == 200
        data = response.json()

        food_sugg = next((s for s in data["suggestions"] if s["category_name"] == "Food & Dining"), None)
        assert food_sugg is not None, f"No Food & Dining suggestion. Got: {[s['category_name'] for s in data['suggestions']]}"
        assert food_sugg["trend"] == "decreasing"
        assert food_sugg["methodology"] == "trend_projection"

    def test_suggest_budgets_handles_outliers(self, client, test_user, test_categories):
        """Outlier months should be detected and excluded from calculations."""
        base_date = datetime(2025, 1, 15)
        amounts = [1000, 1100, 1050, 15000, 1000, 1100, 1050, 1000]
        for i, amt in enumerate(amounts):
            self._create_tx(
                client,
                base_date + timedelta(days=i * 30),
                amt,
                category_name="Food & Dining",
            )

        response = client.get("/api/v1/budgets/suggest", headers=_headers())
        assert response.status_code == 200
        data = response.json()

        food_sugg = next((s for s in data["suggestions"] if s["category_name"] == "Food & Dining"), None)
        assert food_sugg is not None
        # Should NOT suggest something close to 15000
        assert food_sugg["suggested_amount"] < 3000
        assert food_sugg["avg_monthly_spend"] < 2000

    def test_suggest_budgets_volatile_spending_gets_buffer(self, client, test_user, test_categories):
        """Volatile categories should get a larger buffer (median + 20%)."""
        base_date = datetime(2025, 1, 15)
        # High variance, but no consistent trend (stable direction)
        amounts = [800, 1800, 1200, 600, 1600, 1000]
        for i, amt in enumerate(amounts):
            self._create_tx(
                client,
                base_date + timedelta(days=i * 30),
                amt,
                category_name="Food & Dining",
            )

        response = client.get("/api/v1/budgets/suggest", headers=_headers())
        assert response.status_code == 200
        data = response.json()

        food_sugg = next((s for s in data["suggestions"] if s["category_name"] == "Food & Dining"), None)
        assert food_sugg is not None
        assert food_sugg["methodology"] == "median_with_buffer"
        assert "buffer" in food_sugg["rationale"].lower() or "flexibility" in food_sugg["rationale"].lower()

    def test_suggest_budgets_with_single_month_data(self, client, test_user, test_categories):
        """Single month of data should still produce suggestions."""
        base_date = datetime(2025, 1, 1)
        for i in range(5):
            self._create_tx(
                client,
                base_date + timedelta(days=i * 5),
                600,
                category_name="Food & Dining",
            )

        response = client.get("/api/v1/budgets/suggest", headers=_headers())
        assert response.status_code == 200
        data = response.json()

        assert len(data["suggestions"]) > 0
        s = data["suggestions"][0]
        assert s["months_analyzed"] == 1
        assert s["suggested_amount"] > 0
        assert s["trend"] == "stable"

    def test_suggest_budgets_with_uncategorized_transactions(self, client, test_user):
        """Suggestions should include uncategorized transactions."""
        base_date = datetime(2025, 1, 1)
        for i in range(3):
            self._create_tx(
                client,
                base_date + timedelta(days=i * 5),
                500,
                category_name=None,
            )

        response = client.get("/api/v1/budgets/suggest", headers=_headers())
        assert response.status_code == 200
        data = response.json()

        assert len(data["suggestions"]) > 0
        uncategorized = next((s for s in data["suggestions"] if s["category_name"] == "Uncategorized"), None)
        assert uncategorized is not None
        assert uncategorized["avg_monthly_spend"] > 0

    def test_suggest_budgets_ignores_credit_transactions(self, client, test_user, test_categories):
        """Suggestions should only analyze debit transactions, not income."""
        base_date = datetime(2025, 1, 1)

        self._create_tx(client, base_date, 1000, category_name="Food & Dining", tx_type="debit")
        self._create_tx(client, base_date, 50000, category_name="Food & Dining", tx_type="credit")

        response = client.get("/api/v1/budgets/suggest", headers=_headers())
        assert response.status_code == 200
        data = response.json()

        food_sugg = next((s for s in data["suggestions"] if s["category_name"] == "Food & Dining"), None)
        assert food_sugg is not None
        assert food_sugg["avg_monthly_spend"] <= 1500

    def test_suggest_budgets_old_data_still_works(self, client, test_user, test_categories):
        """Old 2025 data queried in 2026 should still produce suggestions."""
        for month in range(1, 13):
            base_date = datetime(2025, month, 15)
            self._create_tx(
                client, base_date,
                1000 + (month * 100),
                category_name="Food & Dining",
            )

        response = client.get("/api/v1/budgets/suggest", headers=_headers())
        assert response.status_code == 200
        data = response.json()

        assert len(data["suggestions"]) > 0
        food_sugg = next((s for s in data["suggestions"] if s["category_name"] == "Food & Dining"), None)
        assert food_sugg is not None
        assert food_sugg["months_analyzed"] >= 6

    def test_suggest_budgets_rationale_is_human_readable(self, client, test_user, test_categories):
        """Rationale should contain currency amounts and be descriptive."""
        base_date = datetime(2025, 1, 15)
        for i in range(6):
            self._create_tx(
                client,
                base_date + timedelta(days=i * 30),
                1500,
                category_name="Food & Dining",
            )

        response = client.get("/api/v1/budgets/suggest", headers=_headers())
        data = response.json()

        s = data["suggestions"][0]
        assert "₹" in s["rationale"]
        assert "/mo" in s["rationale"]

    def test_suggest_budgets_multiple_categories_sorted(self, client, test_user, test_categories):
        """Multiple categories should be sorted by avg spend descending."""
        base_date = datetime(2025, 1, 15)
        for i in range(4):
            dt = base_date + timedelta(days=i * 30)
            self._create_tx(client, dt, 3000, category_name="Food & Dining")
            self._create_tx(client, dt, 1000, category_name="Transportation")
            self._create_tx(client, dt, 2000, category_name="Shopping")

        response = client.get("/api/v1/budgets/suggest", headers=_headers())
        data = response.json()

        suggestions = data["suggestions"]
        assert len(suggestions) == 3, f"Expected 3, got {len(suggestions)}: {[s['category_name'] for s in suggestions]}"
        for i in range(len(suggestions) - 1):
            assert suggestions[i]["avg_monthly_spend"] >= suggestions[i + 1]["avg_monthly_spend"]

    def test_suggest_budgets_backwards_compatible_fields(self, client, test_user, test_categories):
        """Old 'average_spending' and 'reasoning' fields should still be present."""
        base_date = datetime(2025, 1, 15)
        self._create_tx(client, base_date, 1000, category_name="Food & Dining")

        response = client.get("/api/v1/budgets/suggest", headers=_headers())
        data = response.json()

        s = data["suggestions"][0]
        assert "average_spending" in s
        assert "reasoning" in s
        assert s["average_spending"] == s["avg_monthly_spend"]
        assert s["reasoning"] == s["rationale"]
