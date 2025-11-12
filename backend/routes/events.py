"""
Events API routes for ZapStream Backend.

Handles event ingestion with authentication, rate limiting, and idempotency.
"""

from typing import Annotated, Optional
from fastapi import APIRouter, Request, HTTPException, Header, status, Depends
from starlette.requests import Request
from pydantic import ValidationError

from ..models import EventCreate, EventResponse, ErrorResponse
from ..dependencies import TenantId, StorageBackend, AuthenticatedTenant
from ..rate_limit import check_rate_limit
from ..config import get_settings
router = APIRouter()


async def validate_payload_size(payload: dict) -> None:
    """
    Validate that payload size is within limits.

    Args:
        payload: The JSON payload to validate

    Raises:
        HTTPException: 400 if payload is too large
    """
    import json
    payload_str = json.dumps(payload)
    payload_size = len(payload_str.encode('utf-8'))

    max_bytes = get_settings().max_payload_bytes
    if payload_size > max_bytes:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Payload must be a JSON object and <= {max_bytes} bytes"
        )


async def get_idempotency_key(
    request: Request,
    x_idempotency_key: Annotated[Optional[str], Header(alias="X-Idempotency-Key")] = None
) -> Optional[str]:
    """
    Extract idempotency key from headers.

    Args:
        request: FastAPI request object
        x_idempotency_key: Optional idempotency key from header

    Returns:
        Optional[str]: The idempotency key if provided
    """
    return x_idempotency_key


@router.post("", response_model=EventResponse, status_code=status.HTTP_200_OK)
async def create_event(
    request: Request,
    tenant_id: AuthenticatedTenant,
    storage: StorageBackend,
    idempotency_key: Optional[str] = Depends(get_idempotency_key)
):
    """
    Create a new event.

    Accepts JSON events with optional source, type, topic, and payload.
    Supports idempotency via X-Idempotency-Key header.
    Rate limited per tenant.

    Args:
        request: FastAPI request object
        event_data: Event data from request body
        tenant_id: Authenticated tenant ID
        storage: Storage backend instance
        idempotency_key: Optional idempotency key

    Returns:
        EventResponse: Event creation acknowledgment

    Raises:
        HTTPException: 400 for invalid payload
        HTTPException: 401 for authentication errors
        HTTPException: 409 for idempotency conflicts
        HTTPException: 429 for rate limit exceeded
    """
    # Check rate limit
    await check_rate_limit(request)

    # Parse request body manually to tolerate alternative content types
    try:
        raw_body = await request.json()
    except Exception:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="Invalid JSON body"
        )

    try:
        event_data = EventCreate(**raw_body)
    except ValidationError as exc:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=exc.errors()
        )

    # Validate payload size
    await validate_payload_size(event_data.payload)

    try:
        # Check for idempotency conflicts
        if idempotency_key:
            existing_event = await storage.get_by_idempotency(
                tenant_id=tenant_id,
                idempotency_key=idempotency_key
            )
            if existing_event:
                raise HTTPException(
                    status_code=status.HTTP_409_CONFLICT,
                    detail={
                        "error": {
                            "code": "IDEMPOTENCY_CONFLICT",
                            "message": "Event with this idempotency key already exists",
                            "request_id": getattr(request.state, "request_id", "unknown"),
                            "existing_event_id": existing_event.id
                        }
                    }
                )

        # Create the event
        event = await storage.create_event(
            tenant_id=tenant_id,
            source=event_data.source,
            event_type=event_data.type,
            topic=event_data.topic,
            payload=event_data.payload,
            idempotency_key=idempotency_key
        )

        return EventResponse(
            id=event.id,
            received_at=event.created_at,
            status="accepted"
        )

    except HTTPException:
        # Re-raise FastAPI HTTP exceptions
        raise
    except ValueError as exc:
        existing_event_id = None
        if idempotency_key:
            existing_event = await storage.get_by_idempotency(
                tenant_id=tenant_id,
                idempotency_key=idempotency_key
            )
            if existing_event:
                existing_event_id = existing_event.id

        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail={
                "error": {
                    "code": "IDEMPOTENCY_CONFLICT",
                    "message": "Event with this idempotency key already exists",
                    "request_id": getattr(request.state, "request_id", "unknown"),
                    "existing_event_id": existing_event_id
                }
            }
        ) from exc
    except Exception as e:
        # Log the error and return a generic error response
        import logging
        logger = logging.getLogger(__name__)
        logger.error(f"Error creating event: {str(e)}", exc_info=True)

        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail={
                "error": {
                    "code": "INTERNAL_ERROR",
                    "message": "Internal server error",
                    "request_id": getattr(request.state, "request_id", "unknown")
                }
            }
        )
