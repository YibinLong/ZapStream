"""
Pytest configuration and fixtures for ZapStream Backend tests.

Provides shared test setup, fixtures, and utilities.
"""

import os
import tempfile
import pytest
import asyncio
from pathlib import Path
from typing import AsyncGenerator, Generator
from unittest.mock import AsyncMock, MagicMock

from fastapi.testclient import TestClient
from httpx import AsyncClient, ASGITransport

from backend.main import app
from backend.config import get_settings
from backend.storage.base import StorageInterface
from backend.storage.sqlite import SQLiteStorage


@pytest.fixture(scope="session")
def event_loop() -> Generator[asyncio.AbstractEventLoop, None, None]:
    """Create an instance of the default event loop for the test session."""
    loop = asyncio.get_event_loop_policy().new_event_loop()
    yield loop
    loop.close()


@pytest.fixture
def temp_db() -> Generator[str, None, None]:
    """Create a temporary SQLite database for testing."""
    with tempfile.NamedTemporaryFile(suffix=".db", delete=False) as temp_file:
        db_path = temp_file.name

    yield db_path

    # Cleanup
    if os.path.exists(db_path):
        os.unlink(db_path)


@pytest.fixture
def test_settings(temp_db: str) -> None:
    """Override settings for testing."""
    # Store original settings
    original_settings = get_settings()

    # Override with test settings
    test_env_vars = {
        "STORAGE_BACKEND": "sqlite",
        "DATABASE_URL": f"sqlite:///{temp_db}",
        "API_KEYS": "test_key_123=test_tenant,test_key_456=test_tenant_2",
        "LOG_LEVEL": "DEBUG",
        "DEBUG": "true",
        "MAX_PAYLOAD_BYTES": "1024",  # Small for testing
        "RATE_LIMIT_PER_MINUTE": "1000",  # High for testing
        "CORS_ALLOWED_ORIGINS": "http://localhost:3000,http://testclient"
    }

    # Set environment variables
    for key, value in test_env_vars.items():
        os.environ[key] = value

    yield

    # Restore original environment
    for key in test_env_vars:
        os.environ.pop(key, None)


@pytest.fixture
def test_app(test_settings: None) -> None:
    """Create test app with overridden settings."""
    # The app will use the overridden environment variables
    return app


@pytest.fixture
def client(test_app) -> Generator[TestClient, None, None]:
    """Create a test client for the FastAPI app."""
    with TestClient(test_app) as test_client:
        yield test_client


@pytest.fixture
async def async_client(test_app) -> AsyncGenerator[AsyncClient, None]:
    """Create an async test client for the FastAPI app."""
    transport = ASGITransport(app=test_app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        yield ac


@pytest.fixture
async def storage_backend(temp_db: str) -> AsyncGenerator[StorageInterface, None]:
    """Create a storage backend for testing."""
    storage = SQLiteStorage()
    await storage.initialize()
    yield storage
    await storage.close()


@pytest.fixture
def mock_storage() -> AsyncMock:
    """Create a mock storage backend for unit tests."""
    mock = AsyncMock(spec=StorageInterface)

    # Setup default return values
    mock.initialize = AsyncMock(return_value=None)
    mock.close = AsyncMock(return_value=None)
    mock.create_event = AsyncMock(return_value=None)
    mock.get_event_by_id = AsyncMock(return_value=None)
    mock.get_by_idempotency = AsyncMock(return_value=None)
    mock.get_pending_events = AsyncMock(return_value=[])
    mock.acknowledge_event = AsyncMock(return_value=False)
    mock.delete_event = AsyncMock(return_value=False)

    return mock


@pytest.fixture
def valid_api_key() -> str:
    """A valid API key for testing."""
    return "dev_key_123"


@pytest.fixture
def valid_tenant_id() -> str:
    """A valid tenant ID for testing."""
    return "test_tenant"


@pytest.fixture
def invalid_api_key() -> str:
    """An invalid API key for testing."""
    return "invalid_key_789"


@pytest.fixture
def sample_event_payload() -> dict:
    """Sample event payload for testing."""
    return {
        "source": "billing",
        "type": "invoice.paid",
        "topic": "finance",
        "payload": {
            "invoiceId": "inv_123",
            "amount": 4200,
            "currency": "USD"
        }
    }


@pytest.fixture
def sample_event_payload_large() -> dict:
    """Large event payload for testing size limits."""
    return {
        "source": "test",
        "type": "test.large",
        "topic": "test",
        "payload": {
            "data": "x" * 2000  # Large payload
        }
    }


# Test Utilities
def get_auth_headers(api_key: str) -> dict:
    """Get authorization headers for the given API key."""
    return {
        "Authorization": f"Bearer {api_key}",
        "Content-Type": "application/json"
    }


def get_auth_headers_alt(api_key: str) -> dict:
    """Get alternative authorization headers (X-API-Key)."""
    return {
        "X-API-Key": api_key,
        "Content-Type": "application/json"
    }


async def create_test_event(storage: StorageInterface, tenant_id: str = "test_tenant") -> str:
    """Create a test event in storage and return its ID."""
    import uuid

    event = await storage.create_event(
        tenant_id=tenant_id,
        source="test",
        event_type="test.created",
        topic="test",
        payload={"test": True},
        idempotency_key=None
    )
    return event.id


# Markers
pytest.mark.unit = pytest.mark.unit
pytest.mark.integration = pytest.mark.integration
pytest.mark.api = pytest.mark.api
pytest.mark.slow = pytest.mark.slow
