"""
Inbox API routes for ZapStream Backend.

Handles event listing, acknowledgment, and deletion with tenant scoping.
"""

from typing import Annotated, Optional
from datetime import datetime
from fastapi import APIRouter, HTTPException, Query, status, Path
from pydantic import ValidationError

from ..models import InboxResponse, AckResponse, DeleteResponse, EventStatus
from ..dependencies import StorageBackend, AuthenticatedTenant

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


def validate_since_timestamp(since: Optional[str]) -> Optional[datetime]:
    """
    Validate and parse 'since' timestamp parameter.

    Args:
        since: ISO timestamp string

    Returns:
        Optional[datetime]: Parsed datetime if provided, None otherwise

    Raises:
        HTTPException: 400 if timestamp format is invalid
    """
    if not since:
        return None

    try:
        return datetime.fromisoformat(since.replace('Z', '+00:00'))
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Invalid 'since' timestamp format: {str(e)}. Use ISO 8601 format."
        )


@router.get("", response_model=InboxResponse)
async def list_inbox_events(
    tenant_id: AuthenticatedTenant,
    storage: StorageBackend,
    limit: Annotated[int, Query(
        description="Maximum number of events to return",
        ge=1,
        le=500
    )] = 50,
    since: Annotated[Optional[str], Query(
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
        # Validate parameters
        since_dt = validate_since_timestamp(since)
        cursor_data = decode_cursor(cursor)

        # Get pending events from storage
        events, next_event = await storage.get_pending_events(
            tenant_id=tenant_id,
            limit=limit,
            since=since_dt,
            topic=topic,
            event_type=type,
            cursor=cursor_data
        )

        # Convert to response format
        event_items = []
        for event in events:
            event_items.append({
                "id": event.id,
                "created_at": event.created_at,
                "source": event.source,
                "type": event.type,
                "topic": event.topic,
                "payload": event.payload
            })

        # Generate next cursor if there are more events
        next_cursor = None
        if next_event:
            next_cursor = encode_cursor(next_event.created_at, next_event.id)

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