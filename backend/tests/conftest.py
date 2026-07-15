"""Shared test fixtures and configuration."""
import os

# Set test database before any app imports
os.environ["DATABASE_URL"] = "sqlite:///./test_wimm.db"
os.environ["ENVIRONMENT"] = "test"
os.environ["DEBUG"] = "false"

import pytest
from sqlalchemy import create_engine, event
from sqlalchemy.orm import sessionmaker
from fastapi.testclient import TestClient

from app.core.database import Base, get_db
from app.main import app
from app.models import User, Category

# Use SQLite for tests (real database, no mocks)
TEST_DATABASE_URL = "sqlite:///./test_wimm.db"

engine = create_engine(TEST_DATABASE_URL, connect_args={"check_same_thread": False})
TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

TEST_SESSION_TOKEN = "test-session-token-for-testing"


@pytest.fixture(scope="function")
def db_session():
    """Create a fresh database for each test."""
    Base.metadata.create_all(bind=engine)
    session = TestingSessionLocal()
    try:
        yield session
    finally:
        session.close()
        Base.metadata.drop_all(bind=engine)


@pytest.fixture(scope="function")
def client(db_session):
    """Create a test client with database override and auth headers."""
    def override_get_db():
        try:
            yield db_session
        finally:
            pass

    app.dependency_overrides[get_db] = override_get_db
    with TestClient(app) as c:
        yield c
    app.dependency_overrides.clear()


@pytest.fixture
def auth_headers(test_user):
    """Return Authorization headers for the test user."""
    return {"Authorization": f"Bearer {test_user.session_token}"}


@pytest.fixture
def test_user(db_session):
    """Create a test user with a session token."""
    user = User(
        email="test@example.com",
        name="Test User",
        session_token=TEST_SESSION_TOKEN,
    )
    db_session.add(user)
    db_session.commit()
    db_session.refresh(user)
    return user


@pytest.fixture
def test_categories(db_session):
    """Create test categories."""
    categories = [
        Category(name="Food & Dining", icon="🍽️", color="#FF6B6B", is_system=True),
        Category(name="Transportation", icon="🚗", color="#45B7D1", is_system=True),
        Category(name="Shopping", icon="🛍️", color="#DDA0DD", is_system=True),
        Category(name="Utilities", icon="💡", color="#96CEB4", is_system=True),
    ]
    for cat in categories:
        db_session.add(cat)
    db_session.commit()
    for cat in categories:
        db_session.refresh(cat)
    return categories


FIXTURES_DIR = os.path.join(os.path.dirname(__file__), "fixtures")


def get_fixture_path(filename: str) -> str:
    """Get the full path to a test fixture file."""
    return os.path.join(FIXTURES_DIR, filename)
