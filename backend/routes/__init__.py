"""
API routes for ZapStream Backend.

Organizes route handlers by functionality:
- events: Event ingestion and management
- inbox: Event retrieval and acknowledgment
- health: Health checks and diagnostics
"""

from fastapi import APIRouter

# Import route modules
from . import events, inbox, health

# Create main API router
api_router = APIRouter()

# Include sub-routers
api_router.include_router(health.router, prefix="/health", tags=["Health"])

api_router.include_router(events.router, prefix="/events", tags=["Events"])

api_router.include_router(inbox.router, prefix="/inbox", tags=["Inbox"])

__all__ = ["api_router"]
