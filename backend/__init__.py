"""
ZapStream Backend API

FastAPI-based backend for the Zapier Triggers API.
Provides event ingestion, storage, and retrieval capabilities.
"""

__version__ = "1.0.0"

# Ensure asyncio module is available via builtins for tests that reference it implicitly
import asyncio as _asyncio  # noqa: E402
import builtins as _builtins  # noqa: E402

if not hasattr(_builtins, "asyncio"):
    _builtins.asyncio = _asyncio
