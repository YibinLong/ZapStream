"""
Dependency injection functions for ZapStream Backend.

Provides reusable dependencies for authentication, storage, and rate limiting.
"""

from typing import Annotated
import asyncio
from fastapi import Depends, Request
from starlette.requests import Request

from .auth import get_api_key, get_current_tenant_id
from .storage import get_storage_backend, StorageInterface
from .config import get_settings

_storage_init_locks: dict[int, asyncio.Lock] = {}


def _storage_signature() -> tuple[str, str | None]:
    """Build a signature representing the current storage configuration."""
    settings = get_settings()
    if settings.storage_backend == "sqlite":
        return (settings.storage_backend, settings.database_url)
    return (settings.storage_backend, settings.aws_dynamodb_table)


async def get_current_tenant(
    request: Request
) -> str:
    """
    Dependency to get the current tenant ID from an authenticated request.

    This dependency requires that authentication has already been performed
    and the tenant_id has been attached to the request state.

    Returns:
        str: The authenticated tenant ID

    Raises:
        HTTPException: 401 if authentication is required
    """
    return get_current_tenant_id(request)


async def get_storage(
    request: Request
) -> StorageInterface:
    """
    Dependency to get the storage backend instance.

    The storage backend is initialized once per application and stored in
    the app state for efficient reuse across requests. If the lifespan
    handler hasn't run yet (e.g., async tests using httpx directly), the
    storage backend is lazily initialized here.

    Returns:
        StorageInterface: The configured storage backend
    """
    desired_signature = _storage_signature()
    storage = getattr(request.app.state, "storage", None)
    existing_signature = getattr(request.app.state, "storage_signature", None)
    if storage and existing_signature == desired_signature:
        return storage

    loop = asyncio.get_running_loop()
    lock = _storage_init_locks.setdefault(id(loop), asyncio.Lock())

    async with lock:
        storage = getattr(request.app.state, "storage", None)
        existing_signature = getattr(request.app.state, "storage_signature", None)

        if storage and existing_signature == desired_signature:
            return storage

        if storage:
            try:
                await storage.close()
            except Exception:
                pass

        storage = get_storage_backend()
        request.app.state.storage = storage
        request.app.state.storage_signature = desired_signature
        await storage.initialize()

    return request.app.state.storage


# Type aliases for cleaner dependency annotations
TenantId = Annotated[str, Depends(get_current_tenant)]
StorageBackend = Annotated[StorageInterface, Depends(get_storage)]
AuthenticatedTenant = Annotated[str, Depends(get_api_key)]


__all__ = [
    "get_current_tenant",
    "get_storage",
    "TenantId",
    "StorageBackend",
    "AuthenticatedTenant"
]
