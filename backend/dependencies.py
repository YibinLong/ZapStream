"""
Dependency injection functions for ZapStream Backend.

Provides reusable dependencies for authentication, storage, and rate limiting.
"""

from typing import Annotated
from fastapi import Depends, Request
from starlette.requests import Request

from .auth import get_api_key, get_current_tenant_id
from .storage import get_storage_backend, StorageInterface


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
    the app state for efficient reuse across requests.

    Returns:
        StorageInterface: The configured storage backend
    """
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