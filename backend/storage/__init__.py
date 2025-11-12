"""
Storage abstractions for ZapStream Backend.

Provides pluggable storage backends for event persistence.
"""

from ..config import get_settings
from .base import StorageInterface
from .sqlite import SQLiteStorage
from .dynamodb import DynamoDBStorage


def get_storage_backend() -> StorageInterface:
    """
    Factory function to create and return the appropriate storage backend.

    Returns:
        StorageInterface: Configured storage backend instance

    Raises:
        ValueError: If STORAGE_BACKEND is not supported
    """
    settings = get_settings()

    if settings.storage_backend == "sqlite":
        return SQLiteStorage()
    elif settings.storage_backend == "dynamodb":
        return DynamoDBStorage()
    else:
        raise ValueError(f"Unsupported storage backend: {settings.storage_backend}")


__all__ = [
    "StorageInterface",
    "get_storage_backend",
    "SQLiteStorage",
    "DynamoDBStorage",
]
