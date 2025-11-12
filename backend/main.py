from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.exceptions import RequestValidationError
import os
import uuid
from contextlib import asynccontextmanager
from .logging import setup_logging
from .config import get_settings
from .storage import get_storage_backend
from .rate_limit import reset_rate_limiter
from .error_handlers import (
    zapstream_exception_handler,
    http_exception_handler,
    validation_exception_handler,
    general_exception_handler
)

logger = setup_logging()
settings = get_settings()

@asynccontextmanager
async def lifespan(app: FastAPI):
    storage = None
    logger.info("Initializing storage backend...")
    try:
        storage = get_storage_backend()
        app.state.storage = storage
        logger.info(f"Storage backend initialized: {settings.storage_backend}")

        # Initialize database tables
        await storage.initialize()
        logger.info("Database tables created")

        # Reset rate limiter to ensure clean buckets on startup
        reset_rate_limiter()
        logger.info("Rate limiter reset")

    except Exception as e:
        logger.error(f"Failed to initialize storage backend: {e}")
        raise

    logger.info("FastAPI application starting up...")
    try:
        yield
    finally:
        logger.info("FastAPI application shutting down...")
        if storage:
            try:
                await storage.close()
                logger.info("Storage backend closed")
            except Exception as exc:  # pragma: no cover - logging only
                logger.error(f"Failed to close storage backend cleanly: {exc}")

app = FastAPI(
    title="Zapier Triggers API",
    description="Unified, real-time event ingestion and delivery API",
    version="1.0.0",
    lifespan=lifespan
)

# Configure CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins_list,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Request logging and context middleware
@app.middleware("http")
async def add_request_context(request, call_next):
    request_id = str(uuid.uuid4())
    request.state.request_id = request_id

    # Extract tenant_id from request if available (after auth middleware runs)
    tenant_id = None
    if hasattr(request.state, 'tenant_id'):
        tenant_id = request.state.tenant_id

    # Log request start
    logger.info(
        "Request started",
        extra={
            'request_id': request_id,
            'tenant_id': tenant_id,
            'path': request.url.path,
            'method': request.method,
        }
    )

    response = await call_next(request)

    # Add request ID to response headers
    response.headers["X-Request-ID"] = request_id

    # Log request completion
    logger.info(
        "Request completed",
        extra={
            'request_id': request_id,
            'tenant_id': tenant_id,
            'path': request.url.path,
            'method': request.method,
            'status_code': response.status_code,
        }
    )

    return response

# Register exception handlers
from .error_handlers import ZapStreamException

from fastapi import HTTPException
app.add_exception_handler(ZapStreamException, zapstream_exception_handler)
app.add_exception_handler(HTTPException, http_exception_handler)
app.add_exception_handler(RequestValidationError, validation_exception_handler)
app.add_exception_handler(Exception, general_exception_handler)

# Include API routes
from .routes import api_router
app.include_router(api_router)

@app.get("/")
async def root():
    """
    Root endpoint with basic API information.
    """
    return {
        "message": "Zapier Triggers API",
        "version": "1.0.0",
        "docs": "/docs",
        "redoc": "/redoc",
        "health": "/health",
        "events": "/events",
        "inbox": "/inbox"
    }

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(
        "main:app",
        host="0.0.0.0",
        port=settings.effective_port,
        reload=settings.debug,
        log_level=settings.log_level.lower()
    )
