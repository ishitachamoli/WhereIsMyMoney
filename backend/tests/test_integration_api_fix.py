"""
Integration test to verify the API endpoints work with session-based auth.
This tests that all endpoints use the correct /api/v1 prefix and Bearer token auth.
"""

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from app.core.database import Base
from app.main import app
from app.core.database import get_db
from app.models import User, Category

TEST_TOKEN = "integration-test-token-12345"


@pytest.fixture
def db_setup():
    """Setup test database."""
    DATABASE_URL = "sqlite:///./test_wimm_api_fix.db"
    engine = create_engine(
        DATABASE_URL,
        connect_args={"check_same_thread": False},
        echo=False,
    )
    TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

    Base.metadata.create_all(bind=engine)

    def override_get_db():
        db = TestingSessionLocal()
        try:
            yield db
        finally:
            db.close()

    app.dependency_overrides[get_db] = override_get_db

    db = TestingSessionLocal()

    # Create test user with session token
    test_user = User(
        id=1,
        email="test@example.com",
        name="Test User",
        session_token=TEST_TOKEN,
    )
    db.add(test_user)

    # Create system categories
    default_categories = [
        {"name": "Food & Dining", "icon": "🍽️", "color": "#FF6B6B"},
        {"name": "Groceries", "icon": "🛒", "color": "#4ECDC4"},
        {"name": "Transportation", "icon": "🚗", "color": "#45B7D1"},
    ]

    for cat_data in default_categories:
        category = Category(
            name=cat_data["name"],
            icon=cat_data["icon"],
            color=cat_data["color"],
            is_system=True,
            user_id=None,
        )
        db.add(category)

    db.commit()
    db.close()

    yield engine

    app.dependency_overrides.clear()
    Base.metadata.drop_all(bind=engine)


def _headers():
    return {"Authorization": f"Bearer {TEST_TOKEN}"}


def test_api_v1_prefix_transactions(db_setup):
    """Verify /api/v1/transactions endpoint works with Bearer auth."""
    client = TestClient(app)

    response = client.get("/api/v1/transactions", headers=_headers())
    assert response.status_code == 200
    data = response.json()
    assert "items" in data


def test_api_v1_prefix_analytics_spending(db_setup):
    """Verify /api/v1/analytics/spending-by-category works with Bearer auth."""
    client = TestClient(app)

    response = client.get("/api/v1/analytics/spending-by-category", headers=_headers())
    assert response.status_code == 200
    data = response.json()
    assert isinstance(data, list)


def test_api_v1_prefix_analytics_timeline(db_setup):
    """Verify /api/v1/analytics/timeline works with Bearer auth."""
    client = TestClient(app)

    response = client.get(
        "/api/v1/analytics/timeline",
        params={"granularity": "monthly"},
        headers=_headers(),
    )
    assert response.status_code == 200
    data = response.json()
    assert isinstance(data, list)


def test_api_v1_prefix_analytics_income_vs_expenses(db_setup):
    """Verify /api/v1/analytics/income-vs-expenses works with Bearer auth."""
    client = TestClient(app)

    response = client.get(
        "/api/v1/analytics/income-vs-expenses",
        headers=_headers(),
    )
    assert response.status_code == 200
    data = response.json()
    assert isinstance(data, list)


def test_api_v1_prefix_analytics_summary(db_setup):
    """Verify /api/v1/analytics/summary works with Bearer auth."""
    client = TestClient(app)

    response = client.get("/api/v1/analytics/summary", headers=_headers())
    assert response.status_code == 200
    data = response.json()
    assert "total_income" in data


def test_api_v1_prefix_categories(db_setup):
    """Verify /api/v1/categories works with Bearer auth."""
    client = TestClient(app)

    response = client.get("/api/v1/categories", headers=_headers())
    assert response.status_code == 200
    data = response.json()
    assert isinstance(data, list)
    assert len(data) >= 3


def test_api_v1_upload_with_auth(db_setup):
    """Verify /api/v1/upload works with Bearer auth."""
    client = TestClient(app)

    import os
    fixture_path = os.path.join(
        os.path.dirname(__file__), "fixtures/hdfc_statement.csv"
    )

    if os.path.exists(fixture_path):
        with open(fixture_path, "rb") as f:
            response = client.post(
                "/api/v1/upload",
                files={"file": ("hdfc_statement.csv", f, "text/csv")},
                headers=_headers(),
            )
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "success"
        assert data["summary"]["total_transactions"] > 0


def test_auth_session_create(db_setup):
    """Verify POST /api/v1/auth/session creates a new session."""
    client = TestClient(app)

    response = client.post("/api/v1/auth/session", json={"token": None})
    assert response.status_code == 200
    data = response.json()
    assert "token" in data
    assert "user_id" in data
    assert "name" in data


def test_auth_session_validate(db_setup):
    """Verify POST /api/v1/auth/session validates existing token."""
    client = TestClient(app)

    response = client.post("/api/v1/auth/session", json={"token": TEST_TOKEN})
    assert response.status_code == 200
    data = response.json()
    assert data["token"] == TEST_TOKEN
    assert data["user_id"] == 1


def test_auth_me(db_setup):
    """Verify GET /api/v1/auth/me returns user info."""
    client = TestClient(app)

    response = client.get("/api/v1/auth/me", headers=_headers())
    assert response.status_code == 200
    data = response.json()
    assert data["user_id"] == 1
    assert data["name"] == "Test User"


def test_unauthorized_returns_401(db_setup):
    """Verify endpoints return 401 without auth."""
    client = TestClient(app)

    response = client.get("/api/v1/transactions")
    assert response.status_code == 401

    response = client.get("/api/v1/analytics/summary")
    assert response.status_code == 401

    response = client.get("/api/v1/categories")
    assert response.status_code == 401


def test_old_api_paths_return_404(db_setup):
    """Verify old /api/* paths (without v1) return 404."""
    client = TestClient(app)

    old_paths = [
        "/api/transactions",
        "/api/analytics/spending-by-category",
        "/api/analytics/timeline",
        "/api/upload",
        "/api/categories",
    ]

    for path in old_paths:
        response = client.get(path, headers=_headers())
        assert response.status_code == 404, f"Old path {path} should return 404"


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
