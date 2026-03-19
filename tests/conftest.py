"""Pytest fixtures for AI Agent Evaluation Pipeline tests."""
import os
import tempfile
from pathlib import Path
from unittest.mock import patch

import pytest
from fastapi.testclient import TestClient
from fakeredis import FakeRedis

# Set test env before any app imports
_test_db_file = tempfile.NamedTemporaryFile(suffix=".db", delete=False)
_test_db_file.close()
os.environ["DATABASE_URL"] = f"sqlite:///{_test_db_file.name}"
os.environ["REDIS_URL"] = "redis://localhost:6379/0"  # Overridden by FakeRedis

from app.main import app
from app.database import get_db
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

# Test database - use same file so alembic subprocess and app share it
TEST_DATABASE_URL = os.environ["DATABASE_URL"]
test_engine = create_engine(
    TEST_DATABASE_URL,
    connect_args={"check_same_thread": False},
)
TestSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=test_engine)


def override_get_db():
    db = TestSessionLocal()
    try:
        yield db
    finally:
        db.close()


@pytest.fixture(autouse=True)
def _patch_redis():
    """Use FakeRedis instead of real Redis for all tests."""
    fake = FakeRedis(decode_responses=True)
    with patch("app.queue.get_redis", return_value=fake):
        yield fake


@pytest.fixture
def db_session():
    """Provide a clean database session. Tables created via init_db in lifespan."""
    session = TestSessionLocal()
    try:
        yield session
    finally:
        session.rollback()
        session.close()


@pytest.fixture
def client():
    """Test client with overridden DB dependency."""
    app.dependency_overrides[get_db] = override_get_db
    try:
        with TestClient(app) as c:
            yield c
    finally:
        app.dependency_overrides.clear()


