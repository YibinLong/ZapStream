from typing import Optional
from fastapi import HTTPException, Security, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from starlette.requests import Request

from .config import get_settings

settings = get_settings()
security = HTTPBearer(auto_error=False)


async def get_api_key(
    request: Request,
    credentials: Optional[HTTPAuthorizationCredentials] = Security(security)
) -> str:
    """
    Extract and validate API key from request headers.

    Supports two header formats:
    1. Authorization: Bearer <API_KEY>
    2. X-API-Key: <API_KEY>

    Returns:
        tenant_id: The tenant ID associated with the valid API key

    Raises:
        HTTPException: 401 if API key is missing or invalid
    """
    api_key_mapping = settings.api_key_mapping

    # Try Authorization header first
    if credentials and credentials.credentials:
        api_key = credentials.credentials
    else:
        # Fall back to X-API-Key header
        api_key = request.headers.get("X-API-Key")

    if not api_key:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="API key required",
            headers={"WWW-Authenticate": "Bearer"},
        )

    # Look up tenant ID from API key
    tenant_id = api_key_mapping.get(api_key)

    if not tenant_id:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid API key",
            headers={"WWW-Authenticate": "Bearer"},
        )

    # Attach tenant ID to request state for downstream use
    request.state.tenant_id = tenant_id

    return tenant_id


def get_current_tenant_id(request: Request) -> str:
    """
    Get the current tenant ID from the request state.

    This should be called after the auth middleware has run.

    Returns:
        tenant_id: The tenant ID from the authenticated request

    Raises:
        HTTPException: 401 if tenant ID is not found in request state
    """
    tenant_id = getattr(request.state, "tenant_id", None)

    if not tenant_id:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Authentication required",
        )

    return tenant_id