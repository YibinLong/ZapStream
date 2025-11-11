"""
Health check API routes for ZapStream Backend.

Provides health status and diagnostics information.
"""

from datetime import datetime
from fastapi import APIRouter, Depends
from starlette.requests import Request

from ..models import HealthResponse
from ..dependencies import StorageBackend
from ..config import get_settings

router = APIRouter()
settings = get_settings()


@router.get("", response_model=HealthResponse)
async def health_check(request: Request):
    """
    Health check endpoint.

    Returns basic service status information. This endpoint does not require
    authentication and can be used for load balancer health checks.

    Args:
        request: FastAPI request object

    Returns:
        HealthResponse: Service health information
    """
    # Basic health check - in a real implementation, you might want to
    # check database connectivity, external dependencies, etc.
    return HealthResponse(
        status="healthy",
        service="ZapStream Backend",
        version="1.0.0"
    )


@router.get("/detailed")
async def detailed_health_check(request: Request):
    """
    Detailed health check with diagnostics.

    Provides additional diagnostic information about the service and its
    dependencies. This endpoint does not require authentication.

    Args:
        request: FastAPI request object

    Returns:
        dict: Detailed health information
    """
    try:
        # Test storage connectivity
        storage_healthy = True
        storage_type = settings.storage_backend

        # In a real implementation, you might perform a simple query
        # to test database connectivity here

        return {
            "status": "healthy" if storage_healthy else "unhealthy",
            "service": "ZapStream Backend",
            "version": "1.0.0",
            "timestamp": datetime.utcnow().isoformat() + "Z",
            "environment": settings.app_env,
            "components": {
                "storage": {
                    "type": storage_type,
                    "status": "healthy" if storage_healthy else "unhealthy"
                }
            }
        }
    except Exception as e:
        return {
            "status": "unhealthy",
            "service": "ZapStream Backend",
            "version": "1.0.0",
            "timestamp": datetime.utcnow().isoformat() + "Z",
            "error": str(e)
        }