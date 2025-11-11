from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
import os
import uuid
from contextlib import asynccontextmanager
from typing import Dict

from .logging import setup_logging
from .config import get_settings

logger = setup_logging()
settings = get_settings()

@asynccontextmanager
async def lifespan(app: FastAPI):
    logger.info("FastAPI application starting up...")
    yield
    logger.info("FastAPI application shutting down...")

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

# Request ID middleware
@app.middleware("http")
async def add_request_id(request, call_next):
    request_id = str(uuid.uuid4())
    request.state.request_id = request_id

    response = await call_next(request)
    response.headers["X-Request-ID"] = request_id

    return response

@app.get("/health")
async def health_check():
    """
    Health check endpoint for monitoring and load balancers.
    Returns 200 OK when the service is healthy.
    """
    return {
        "status": "healthy",
        "service": "Zapier Triggers API",
        "version": "1.0.0"
    }

@app.get("/")
async def root():
    """
    Root endpoint with basic API information.
    """
    return {
        "message": "Zapier Triggers API",
        "version": "1.0.0",
        "docs": "/docs",
        "health": "/health"
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