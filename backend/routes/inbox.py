"""
Inbox API routes for ZapStream Backend.

Handles event listing, acknowledgment, deletion, and real-time streaming with tenant scoping.
"""

from typing import Annotated, Optional
from datetime import datetime, timezone
import json
import asyncio
from fastapi import APIRouter, HTTPException, Query, status, Path, Request
from fastapi.responses import StreamingResponse
from pydantic import ValidationError

from ..models import InboxResponse, AckResponse, DeleteResponse, EventStatus
from ..dependencies import StorageBackend, AuthenticatedTenant
from ..rate_limit import check_rate_limit
from ..auth import get_api_key_for_sse

router = APIRouter()


def decode_cursor(cursor: Optional[str]) -> Optional[tuple]:
    """
    Decode pagination cursor into (created_at, event_id) tuple.

    Args:
        cursor: Encoded cursor string in format "timestamp|event_id"

    Returns:
        Optional[tuple]: (created_at, event_id) if cursor provided, None otherwise

    Raises:
        HTTPException: 400 if cursor format is invalid
    """
    if not cursor:
        return None

    try:
        parts = cursor.split('|', 1)
        if len(parts) != 2:
            raise ValueError("Invalid cursor format")

        created_at_str, event_id = parts
        created_at = datetime.fromisoformat(created_at_str.replace('Z', '+00:00'))
        return (created_at, event_id)
    except (ValueError, IndexError) as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Invalid cursor format: {str(e)}"
        )


def encode_cursor(created_at: datetime, event_id: str) -> str:
    """
    Encode (created_at, event_id) into cursor string.

    Args:
        created_at: Event creation timestamp
        event_id: Event ID

    Returns:
        str: Encoded cursor string
    """
    # Use ISO format with Z suffix for UTC
    created_at_str = created_at.isoformat().replace('+00:00', 'Z')
    return f"{created_at_str}|{event_id}"


# Rely on FastAPI/Pydantic to validate 'since' as a datetime to produce 422 on invalid values


@router.get("", response_model=InboxResponse)
async def list_inbox_events(
    request: Request,
    tenant_id: AuthenticatedTenant,
    storage: StorageBackend,
    limit: Annotated[int, Query(
        description="Maximum number of events to return",
        ge=1,
        le=500
    )] = 50,
    since: Annotated[Optional[datetime], Query(
        description="Return events created after this ISO timestamp"
    )] = None,
    topic: Annotated[Optional[str], Query(
        description="Filter by event topic"
    )] = None,
    type: Annotated[Optional[str], Query(
        description="Filter by event type"
    )] = None,
    cursor: Annotated[Optional[str], Query(
        description="Pagination cursor for next page"
    )] = None
):
    """
    List undelivered events from the tenant's inbox.

    Supports filtering by topic, type, and timestamp. Uses cursor-based pagination
    for efficient iteration through large result sets.

    Args:
        tenant_id: Authenticated tenant ID
        storage: Storage backend instance
        limit: Maximum events to return (1-500, default 50)
        since: ISO timestamp to filter events created after
        topic: Optional topic filter
        type: Optional type filter
        cursor: Pagination cursor from previous response

    Returns:
        InboxResponse: List of events and optional next cursor

    Raises:
        HTTPException: 400 for invalid query parameters
        HTTPException: 401 for authentication errors
    """
    try:
        await check_rate_limit(request)
        cursor_data = decode_cursor(cursor)

        # Get pending events from storage
        events, next_cursor = await storage.get_pending_events(
            tenant_id=tenant_id,
            limit=limit,
            since=since,
            topic=topic,
            event_type=type,
            cursor=cursor_data
        )

        # Convert to response format
        event_items = []
        for event in events:
            event_items.append({
                "id": event.id,
                "created_at": event.created_at.isoformat().replace("+00:00", "Z"),
                "source": event.source,
                "type": event.type,
                "topic": event.topic,
                "payload": event.payload
            })

        return InboxResponse(
            events=event_items,
            next_cursor=next_cursor
        )

    except HTTPException:
        # Re-raise FastAPI HTTP exceptions
        raise
    except Exception as e:
        # Log the error and return a generic error response
        import logging
        logger = logging.getLogger(__name__)
        logger.error(f"Error listing inbox events: {str(e)}", exc_info=True)

        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail={
                "error": {
                    "code": "INTERNAL_ERROR",
                    "message": "Internal server error",
                    "request_id": "unknown"  # Would be set by middleware
                }
            }
        )


@router.post("/{event_id}/ack", response_model=AckResponse)
async def acknowledge_event(
    request: Request,
    tenant_id: AuthenticatedTenant,
    storage: StorageBackend,
    event_id: Annotated[str, Path(
        description="ID of the event to acknowledge"
    )]
):
    """
    Acknowledge an event as delivered/processed.

    Marks the event as delivered and changes status to acknowledged.
    This operation is idempotent - acknowledging an already acknowledged
    event will return 200 OK.

    Args:
        tenant_id: Authenticated tenant ID
        storage: Storage backend instance
        event_id: ID of the event to acknowledge

    Returns:
        AckResponse: Acknowledgment confirmation

    Raises:
        HTTPException: 404 if event not found for tenant
        HTTPException: 401 for authentication errors
        HTTPException: 409 if event is in invalid state
    """
    try:
        await check_rate_limit(request)
        # Get the event first to ensure it exists and belongs to the tenant
        event = await storage.get_event_by_id(event_id, tenant_id)

        if not event or event.tenant_id != tenant_id:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Event not found"
            )

        # Check if event can be acknowledged
        if event.status == EventStatus.DELETED:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail={
                    "error": {
                        "code": "INVALID_STATE_TRANSITION",
                        "message": "Cannot acknowledge deleted event",
                        "request_id": "unknown",
                        "current_status": event.status
                    }
                }
            )

        # Acknowledge the event (idempotent operation)
        await storage.acknowledge_event(event_id, tenant_id)

        return AckResponse(
            id=event_id,
            status="acknowledged"
        )

    except HTTPException:
        # Re-raise FastAPI HTTP exceptions
        raise
    except Exception as e:
        # Log the error and return a generic error response
        import logging
        logger = logging.getLogger(__name__)
        logger.error(f"Error acknowledging event {event_id}: {str(e)}", exc_info=True)

        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail={
                "error": {
                    "code": "INTERNAL_ERROR",
                    "message": "Internal server error",
                    "request_id": "unknown"
                }
            }
        )


@router.delete("/{event_id}", response_model=DeleteResponse)
async def delete_event(
    request: Request,
    tenant_id: AuthenticatedTenant,
    storage: StorageBackend,
    event_id: Annotated[str, Path(
        description="ID of the event to delete"
    )]
):
    """
    Delete an event from the inbox.

    Permanently removes the event from storage. This operation cannot be undone.
    Deletion is only allowed for events in 'pending' or 'acknowledged' status.

    Args:
        tenant_id: Authenticated tenant ID
        storage: Storage backend instance
        event_id: ID of the event to delete

    Returns:
        DeleteResponse: Deletion confirmation

    Raises:
        HTTPException: 404 if event not found for tenant
        HTTPException: 401 for authentication errors
        HTTPException: 409 if event is already deleted
    """
    try:
        await check_rate_limit(request)
        # Get the event first to ensure it exists and belongs to the tenant
        event = await storage.get_event_by_id(event_id, tenant_id)

        if not event or event.tenant_id != tenant_id:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Event not found"
            )

        # Check if event can be deleted
        if event.status == EventStatus.DELETED:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail={
                    "error": {
                        "code": "ALREADY_DELETED",
                        "message": "Event is already deleted",
                        "request_id": "unknown"
                    }
                }
            )

        # Delete the event
        await storage.delete_event(event_id, tenant_id)

        return DeleteResponse(
            id=event_id,
            status="deleted"
        )

    except HTTPException:
        # Re-raise FastAPI HTTP exceptions
        raise
    except Exception as e:
        # Log the error and return a generic error response
        import logging
        logger = logging.getLogger(__name__)
        logger.error(f"Error deleting event {event_id}: {str(e)}", exc_info=True)

        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail={
                "error": {
                    "code": "INTERNAL_ERROR",
                    "message": "Internal server error",
                    "request_id": "unknown"
                }
            }
        )

@router.get("/stream")
async def stream_events(
    tenant_id: Annotated[str, get_api_key_for_sse],
    storage: StorageBackend
):
    """
    Server-Sent Events endpoint for real-time event updates.

    Provides a streaming connection that pushes new events to the client
    as they are created. Clients can maintain an open connection to receive
    real-time updates without polling.

    Args:
        tenant_id: Tenant ID authenticated via API key (supports both headers and ?api_key= query param)
        storage: Storage backend instance

    Returns:
        StreamingResponse: SSE stream with real-time event updates

    Raises:
        HTTPException: 401 for authentication errors
    """
    async def event_stream():
        """Generate SSE events for real-time updates."""

        # Track the last seen event timestamp to avoid duplicates
        last_seen = datetime.now(timezone.utc)

        try:
            while True:
                try:
                    # Get events created since last check
                    events, _ = await storage.get_pending_events(
                        tenant_id=tenant_id,
                        limit=100,  # Get up to 100 recent events
                        since=last_seen,
                        topic=None,
                        event_type=None,
                        cursor=None
                    )

                    # Send each new event as an SSE message
                    for event in events:
                        # Ensure both datetimes are timezone-aware for comparison
                        event_time = event.created_at
                        if event_time.tzinfo is None:
                            event_time = event_time.replace(tzinfo=timezone.utc)

                        if event_time > last_seen:
                            event_data = {
                                "id": event.id,
                                "created_at": event.created_at.isoformat(),
                                "source": event.source,
                                "type": event.type,
                                "topic": event.topic,
                                "payload": event.payload,
                                "status": event.status,
                                "delivered": event.delivered
                            }

                            # Format as SSE message
                            sse_message = f"data: {json.dumps(event_data)}\n\n"
                            yield sse_message

                            # Update last seen timestamp (use timezone-aware version)
                            last_seen = event_time

                    # Send heartbeat every 10 seconds to keep connection alive
                    yield ": heartbeat\n\n"

                    # Wait before next poll
                    await asyncio.sleep(2)

                except Exception as e:
                    # Log error but keep stream alive
                    import logging
                    logger = logging.getLogger(__name__)
                    logger.error(f"Error in event stream for tenant {tenant_id}: {str(e)}")

                    # Send error message to client
                    error_data = {
                        "type": "error",
                        "message": "Internal stream error, continuing...",
                        "timestamp": datetime.now(timezone.utc).isoformat()
                    }
                    yield f"data: {json.dumps(error_data)}\n\n"

                    # Wait before retrying
                    await asyncio.sleep(5)

        except asyncio.CancelledError:
            # Client disconnected cleanly
            import logging
            logger = logging.getLogger(__name__)
            logger.info(f"Event stream disconnected for tenant {tenant_id}")
            raise
        except Exception as e:
            # Unexpected error in the stream generator
            import logging
            logger = logging.getLogger(__name__)
            logger.error(f"Unexpected error in event stream for tenant {tenant_id}: {str(e)}", exc_info=True)
            raise

    return StreamingResponse(
        event_stream(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no"  # Disable nginx buffering
        }
    )
