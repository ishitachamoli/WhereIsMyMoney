"""Integration tests for the monthly personality tabs + year recap feature.

These tests exercise real code paths: they insert real Transaction rows into a
real (SQLite) database via the shared fixtures, then call both the service
functions and the HTTP endpoints. No mocks.
"""
from __future__ import annotations

from datetime import datetime, timezone

import pytest

from app.models.transaction import Transaction, TransactionType
from app.services.ai_summary_service import (
    generate_monthly_summary,
    generate_yearly_recap,
    get_available_months,
)
from app.services import tone_templates
from tests.conftest import TEST_SESSION_TOKEN


def _headers():
    return {"Authorization": f"Bearer {TEST_SESSION_TOKEN}"}


def _mk_txn(user_id, category, date, amount, ttype, description, currency="EUR"):
    return Transaction(
        user_id=user_id,
        category_id=category.id if category else None,
        date=date,
        description=description,
        amount=amount,
        transaction_type=ttype,
        currency=currency,
    )


@pytest.fixture
def seeded_year(db_session, test_user, test_categories):
    """Seed a spread of transactions across 2025 for the test user."""
    food = next(c for c in test_categories if c.name == "Food & Dining")
    shopping = next(c for c in test_categories if c.name == "Shopping")
    transport = next(c for c in test_categories if c.name == "Transportation")

    txns = []
    # March 2025 — heavy food + shopping
    for day in range(1, 11):
        txns.append(_mk_txn(test_user.id, food,
                             datetime(2025, 3, day, 12, 0, tzinfo=timezone.utc),
                             420.0, TransactionType.DEBIT, f"SWIGGY ORDER {day}"))
    for day in range(1, 6):
        txns.append(_mk_txn(test_user.id, shopping,
                             datetime(2025, 3, day, 14, 0, tzinfo=timezone.utc),
                             1200.0, TransactionType.DEBIT, f"AMAZON PURCHASE {day}"))
    txns.append(_mk_txn(test_user.id, None,
                        datetime(2025, 3, 1, 9, 0, tzinfo=timezone.utc),
                        20000.0, TransactionType.CREDIT, "SALARY MARCH"))

    # February 2025 — lighter (used as previous-month comparison for March)
    for day in range(1, 4):
        txns.append(_mk_txn(test_user.id, food,
                             datetime(2025, 2, day, 12, 0, tzinfo=timezone.utc),
                             300.0, TransactionType.DEBIT, f"ZOMATO ORDER {day}"))
    txns.append(_mk_txn(test_user.id, None,
                        datetime(2025, 2, 1, 9, 0, tzinfo=timezone.utc),
                        20000.0, TransactionType.CREDIT, "SALARY FEB"))

    # September 2025 — small month
    txns.append(_mk_txn(test_user.id, transport,
                        datetime(2025, 9, 5, 8, 0, tzinfo=timezone.utc),
                        150.0, TransactionType.DEBIT, "METRO CARD"))
    txns.append(_mk_txn(test_user.id, None,
                        datetime(2025, 9, 1, 9, 0, tzinfo=timezone.utc),
                        20000.0, TransactionType.CREDIT, "SALARY SEP"))

    for t in txns:
        db_session.add(t)
    db_session.commit()
    return test_user


# ─── Service-level tests ─────────────────────────────────────────────────────


def test_available_months(db_session, seeded_year):
    months = get_available_months(db_session, seeded_year.id)
    keys = [m["month"] for m in months]
    assert "2025-03" in keys
    assert "2025-02" in keys
    assert "2025-09" in keys
    # Newest-first ordering
    assert keys == sorted(keys, reverse=True)
    march = next(m for m in months if m["month"] == "2025-03")
    assert march["label"] == "March 2025"
    assert march["transaction_count"] > 0


@pytest.mark.parametrize("tone", ["roast", "praise", "executive", "fun"])
def test_monthly_summary_all_tones(db_session, seeded_year, tone):
    result = generate_monthly_summary(db_session, seeded_year.id, "2025-03", tone)
    assert result["tone"] == tone
    assert result["month"] == "2025-03"
    assert result["month_label"] == "March 2025"
    assert result["has_data"] is True
    assert result["currency_symbol"] == "€"
    assert len(result["lines"]) > 0
    # Every line must be a non-empty phrased string
    for line in result["lines"]:
        assert line["text"]
    # Stats reused across tones — totals must be tone-independent
    assert result["stats"]["total_spent"] > 0
    assert result["stats"]["top_categories"]


def test_monthly_summary_same_stats_different_phrasing(db_session, seeded_year):
    roast = generate_monthly_summary(db_session, seeded_year.id, "2025-03", "roast")
    exec_ = generate_monthly_summary(db_session, seeded_year.id, "2025-03", "executive")
    # Same underlying numbers
    assert roast["stats"]["total_spent"] == exec_["stats"]["total_spent"]
    # Different phrasing
    roast_text = " ".join(l["text"] for l in roast["lines"])
    exec_text = " ".join(l["text"] for l in exec_["lines"])
    assert roast_text != exec_text
    # Roast tone uses an emoji icon on its opener; executive uses bullets only
    roast_icons = {l["icon"] for l in roast["lines"]}
    exec_icons = {l["icon"] for l in exec_["lines"]}
    assert "🔥" in roast_icons
    assert exec_icons == {"•"}


def test_monthly_summary_currency_symbol_in_amounts(db_session, seeded_year):
    fun = generate_monthly_summary(db_session, seeded_year.id, "2025-03", "fun")
    joined = " ".join(l["text"] for l in fun["lines"])
    assert "€" in joined  # dominant currency reflected in phrasing


def test_monthly_summary_invalid_tone_raises(db_session, seeded_year):
    with pytest.raises(ValueError):
        generate_monthly_summary(db_session, seeded_year.id, "2025-03", "sassy")


def test_monthly_summary_empty_month(db_session, seeded_year):
    result = generate_monthly_summary(db_session, seeded_year.id, "2025-07", "roast")
    assert result["has_data"] is False
    assert result["stats"]["transaction_count"] == 0


def test_yearly_recap(db_session, seeded_year):
    recap = generate_yearly_recap(db_session, seeded_year.id, 2025)
    assert recap["has_data"] is True
    assert recap["year"] == 2025
    assert recap["currency_symbol"] == "€"
    assert recap["personality_title"]
    assert recap["headline_stats"]["total_spent"] > 0
    assert recap["headline_stats"]["total_income"] > 0
    assert recap["headline_stats"]["biggest_month"] == "March"
    assert recap["headline_stats"]["smallest_month"] == "September"
    assert len(recap["top_categories"]) > 0
    assert len(recap["biggest_transactions"]) > 0
    assert recap["narrative"]


def test_yearly_recap_empty_year(db_session, seeded_year):
    recap = generate_yearly_recap(db_session, seeded_year.id, 2020)
    assert recap["has_data"] is False
    assert recap["headline_stats"]["transaction_count"] == 0


# ─── HTTP endpoint tests ─────────────────────────────────────────────────────


def test_endpoint_available_months(client, seeded_year):
    resp = client.get("/api/v1/ai/summary/available-months", headers=_headers())
    assert resp.status_code == 200
    data = resp.json()
    assert "months" in data
    assert any(m["month"] == "2025-03" for m in data["months"])


def test_endpoint_monthly_all_tones(client, seeded_year):
    for tone in tone_templates.VALID_TONES:
        resp = client.get(
            "/api/v1/ai/summary/monthly",
            params={"month": "2025-03", "tone": tone},
            headers=_headers(),
        )
        assert resp.status_code == 200, resp.text
        data = resp.json()
        assert data["tone"] == tone
        assert data["lines"]


def test_endpoint_monthly_invalid_tone(client, seeded_year):
    resp = client.get(
        "/api/v1/ai/summary/monthly",
        params={"month": "2025-03", "tone": "grumpy"},
        headers=_headers(),
    )
    assert resp.status_code == 400


def test_endpoint_monthly_invalid_month_format(client, seeded_year):
    resp = client.get(
        "/api/v1/ai/summary/monthly",
        params={"month": "2025/03", "tone": "roast"},
        headers=_headers(),
    )
    assert resp.status_code in (400, 422)


def test_endpoint_yearly(client, seeded_year):
    resp = client.get(
        "/api/v1/ai/summary/yearly",
        params={"year": 2025},
        headers=_headers(),
    )
    assert resp.status_code == 200, resp.text
    data = resp.json()
    assert data["year"] == 2025
    assert data["has_data"] is True
    assert data["personality_title"]


def test_endpoint_legacy_summary_still_works(client, seeded_year):
    """Backward compatibility: the original endpoint must keep functioning."""
    resp = client.get("/api/v1/ai/summary", headers=_headers())
    assert resp.status_code == 200
    data = resp.json()
    assert "overview" in data
    assert "spending_personality" in data
