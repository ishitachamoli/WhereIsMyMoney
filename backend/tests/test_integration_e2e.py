#!/usr/bin/env python3
"""End-to-end integration test for WhereIsMyMoneyGoing.

Tests the full flow: upload CSV → parse → classify → analytics.
Run from the backend/ directory:
    python tests/test_integration_e2e.py
"""

import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

os.environ["DATABASE_URL"] = "sqlite:///./test_e2e_run.db"
os.environ["ENVIRONMENT"] = "development"
os.environ["DEBUG"] = "false"

from app.core.database import Base, init_db, get_session_local
from app.models import User, Transaction, Category, BankStatement, ClassificationRule

E2E_TOKEN = "e2e-test-session-token-xyz"


def setup_db():
    """Create fresh test database with seeded data."""
    db_path = "./test_e2e_run.db"
    if os.path.exists(db_path):
        os.remove(db_path)

    init_db(os.environ["DATABASE_URL"])
    SessionLocal = get_session_local()
    db = SessionLocal()

    user = User(email="test@test.com", name="Test User", session_token=E2E_TOKEN)
    db.add(user)

    categories = [
        "Food & Dining", "Groceries", "Transportation", "Utilities",
        "Entertainment", "Shopping", "Healthcare", "Education",
        "Rent & Housing", "Insurance", "Investments", "Salary",
        "Transfer", "Transfers", "EMI & Loans", "Subscriptions",
        "Travel", "Other", "Income", "Cash", "Bills & Fees",
        "Personal Care", "Home",
    ]
    for name in categories:
        db.add(Category(name=name, is_system=True, user_id=None))

    db.commit()
    db.close()
    return SessionLocal


def run_tests():
    """Run all integration tests."""
    SessionLocal = setup_db()

    from fastapi.testclient import TestClient
    from app.main import app

    client = TestClient(app)
    headers = {"Authorization": f"Bearer {E2E_TOKEN}"}
    passed = 0
    failed = 0

    def check(name, condition, detail=""):
        nonlocal passed, failed
        if condition:
            print(f"  ✅ {name}")
            passed += 1
        else:
            print(f"  ❌ {name}: {detail}")
            failed += 1

    print("=" * 60)
    print("  WhereIsMyMoneyGoing — Integration Test Suite")
    print("=" * 60)

    # Test 1: Health check
    print("\n🏥 Health Check")
    resp = client.get("/health")
    check("GET /health returns 200", resp.status_code == 200)
    check("Response contains status=healthy", resp.json().get("status") == "healthy")

    # Test 1.5: Auth endpoints
    print("\n🔐 Auth API")
    resp = client.post("/api/v1/auth/session", json={"token": E2E_TOKEN})
    check("Validate session returns 200", resp.status_code == 200)
    check("Token matches", resp.json()["token"] == E2E_TOKEN)

    resp = client.get("/api/v1/auth/me", headers=headers)
    check("GET /auth/me returns 200", resp.status_code == 200)
    check("User name is Test User", resp.json()["name"] == "Test User")

    # Test 2: Upload bank statement
    print("\n📤 Upload Bank Statement")
    fixture_path = os.path.join(
        os.path.dirname(__file__), "fixtures", "sample_hdfc_statement.csv"
    )
    with open(fixture_path, "rb") as f:
        resp = client.post(
            "/api/v1/upload",
            files={"file": ("hdfc_statement.csv", f, "text/csv")},
            headers=headers,
        )
    check("POST /upload returns 200", resp.status_code == 200)
    data = resp.json()
    check("Status is success", data["status"] == "success")
    check("16 transactions parsed", data["summary"]["total_transactions"] == 16)

    # Test 3: Verify auto-classification
    print("\n🏷️  Auto-Classification")
    db = SessionLocal()
    txns = db.query(Transaction).all()
    classified = [t for t in txns if t.category_id is not None]
    check(f"All transactions stored ({len(txns)})", len(txns) == 16)
    pct = len(classified) * 100 // len(txns) if txns else 0
    check(f"Classification rate >= 90% (got {pct}%)", pct >= 90)
    db.close()

    # Test 4: Transactions endpoint
    print("\n📋 Transactions API")
    resp = client.get("/api/v1/transactions", headers=headers)
    check("GET /transactions returns 200", resp.status_code == 200)
    tdata = resp.json()
    check("Returns paginated response", "items" in tdata and "total" in tdata)
    check(f"Total matches ({tdata['total']})", tdata["total"] == 16)

    # Test 4.5: Unauthorized returns 401
    resp = client.get("/api/v1/transactions")
    check("No auth → 401", resp.status_code == 401)

    # Test 5: Analytics endpoints
    print("\n📊 Analytics")
    resp = client.get("/api/v1/analytics/spending-by-category", headers=headers)
    check("Spending by category returns 200", resp.status_code == 200)
    categories_resp = resp.json()
    check("Multiple categories returned", len(categories_resp) >= 3)

    resp = client.get("/api/v1/analytics/income-vs-expenses", headers=headers)
    check("Income vs expenses returns 200", resp.status_code == 200)

    # Test 6: Classification API
    print("\n🤖 Classification API")
    resp = client.post("/api/v1/classify", json={
        "description": "UPI-SWIGGY-ORDERS@PAYTM",
        "amount": -450.0,
        "transaction_type": "debit",
    })
    check("Single classify returns 200", resp.status_code == 200)
    cls_data = resp.json()
    check("Classified as Food & Dining", cls_data["category"] == "Food & Dining")
    check("High confidence (>=0.9)", cls_data["confidence"] >= 0.9)

    resp = client.post("/api/v1/classify/batch", json={
        "transactions": [
            {"description": "SHELL PETROL PUMP", "amount": -2500.0},
            {"description": "SALARY CREDIT", "amount": 85000.0},
        ]
    })
    check("Batch classify returns 200", resp.status_code == 200)
    batch = resp.json()
    check("Batch returns 2 results", batch["total"] == 2)

    # Test 7: Categories API
    print("\n📂 Categories API")
    resp = client.get("/api/v1/categories", headers=headers)
    check("GET /categories returns 200", resp.status_code == 200)

    # Test 8: Classification stats
    print("\n📈 Classification Stats")
    resp = client.get("/api/v1/classify/stats")
    check("Stats endpoint returns 200", resp.status_code == 200)
    stats = resp.json()
    check("Pipeline stats present", "pipeline_stats" in stats)

    # Summary
    print("\n" + "=" * 60)
    total = passed + failed
    if failed == 0:
        print(f"  ✅ ALL {total} TESTS PASSED")
    else:
        print(f"  ❌ {failed}/{total} TESTS FAILED")
    print("=" * 60)

    # Cleanup
    db_path = "./test_e2e_run.db"
    if os.path.exists(db_path):
        os.remove(db_path)

    return failed == 0


if __name__ == "__main__":
    success = run_tests()
    sys.exit(0 if success else 1)
