import uuid
from datetime import datetime
from typing import Optional, Dict, Any, List
from enum import Enum

from pydantic import BaseModel, Field, ConfigDict
from sqlmodel import SQLModel, Field as SQLField
from sqlalchemy import Column, JSON
from sqlalchemy.types import JSON as SQLAlchemyJSON


class EventStatus(str, Enum):
    """Event status enumeration."""
    PENDING = "pending"
    ACKNOWLEDGED = "acknowledged"
    DELETED = "deleted"


class EventBase(SQLModel):
    """Base Event model with common fields."""
    tenant_id: str = Field(index=True, description="Tenant identifier")
    source: Optional[str] = Field(default=None, description="Event source (e.g., 'billing')")
    type: Optional[str] = Field(default=None, description="Event type (e.g., 'invoice.paid')")
    topic: Optional[str] = Field(default=None, description="Event topic (e.g., 'finance')")
    payload: Optional[Dict[str, Any]] = Field(default=None, description="JSON payload containing event data")
    delivered: bool = Field(default=False, description="Whether event has been delivered")
    status: EventStatus = Field(default=EventStatus.PENDING, description="Event processing status")
    idempotency_key: Optional[str] = Field(
        default=None,
        description="Optional idempotency key for safe retries"
    )


class Event(EventBase, table=True):
    """Event database model."""
    __tablename__ = "events"

    id: str = SQLField(
        default_factory=lambda: str(uuid.uuid4()),
        primary_key=True,
        description="Unique event identifier"
    )
    tenant_id: str = SQLField(index=True, description="Tenant identifier")
    source: Optional[str] = SQLField(default=None, description="Event source (e.g., 'billing')")
    type: Optional[str] = SQLField(default=None, description="Event type (e.g., 'invoice.paid')")
    topic: Optional[str] = SQLField(default=None, description="Event topic (e.g., 'finance')")
    payload: Optional[Dict[str, Any]] = SQLField(default=None, sa_column=Column(JSON), description="JSON payload containing event data")
    delivered: bool = SQLField(default=False, description="Whether event has been delivered")
    status: EventStatus = SQLField(default=EventStatus.PENDING, description="Event processing status")
    idempotency_key: Optional[str] = SQLField(
        default=None,
        index=True,
        description="Optional idempotency key for safe retries"
    )
    created_at: datetime = SQLField(
        default_factory=datetime.utcnow,
        description="Event creation timestamp"
    )
    updated_at: datetime = SQLField(
        default_factory=datetime.utcnow,
        description="Last update timestamp"
    )


class EventCreate(BaseModel):
    """Request model for creating events."""
    source: Optional[str] = None
    type: Optional[str] = None
    topic: Optional[str] = None
    payload: Dict[str, Any]

    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "source": "billing",
                "type": "invoice.paid",
                "topic": "finance",
                "payload": {
                    "invoiceId": "inv_123",
                    "amount": 4200,
                    "currency": "USD"
                }
            }
        }
    )


class EventResponse(BaseModel):
    """Response model for event creation."""
    id: str
    received_at: datetime
    status: str

    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "id": "evt_01HH...",
                "received_at": "2025-11-11T10:00:00Z",
                "status": "accepted"
            }
        }
    )


class EventListItem(BaseModel):
    """Model for events in inbox listing."""
    id: str
    created_at: datetime
    source: Optional[str] = None
    type: Optional[str] = None
    topic: Optional[str] = None
    payload: Dict[str, Any]

    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "id": "evt_01HH...",
                "created_at": "2025-11-11T10:00:00Z",
                "source": "billing",
                "type": "invoice.paid",
                "topic": "finance",
                "payload": {
                    "invoiceId": "inv_123",
                    "amount": 4200,
                    "currency": "USD"
                }
            }
        }
    )


class InboxResponse(BaseModel):
    """Response model for inbox listing."""
    events: List[EventListItem]
    next_cursor: Optional[str] = None

    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "events": [
                    {
                        "id": "evt_01HH...",
                        "created_at": "2025-11-11T10:00:00Z",
                        "source": "billing",
                        "type": "invoice.paid",
                        "topic": "finance",
                        "payload": {
                            "invoiceId": "inv_123",
                            "amount": 4200,
                            "currency": "USD"
                        }
                    }
                ],
                "next_cursor": "2025-11-11T10:00:00Z|evt_01HH..."
            }
        }
    )


class AckResponse(BaseModel):
    """Response model for event acknowledgment."""
    id: str
    status: str

    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "id": "evt_01HH...",
                "status": "acknowledged"
            }
        }
    )


class DeleteResponse(BaseModel):
    """Response model for event deletion."""
    id: str
    status: str

    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "id": "evt_01HH...",
                "status": "deleted"
            }
        }
    )


class ErrorResponse(BaseModel):
    """Standard error response format."""
    error: Dict[str, Any]

    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "error": {
                    "code": "INVALID_PAYLOAD",
                    "message": "Payload must be a JSON object and <= 512KB",
                    "request_id": "req_01HH..."
                }
            }
        }
    )


class HealthResponse(BaseModel):
    """Health check response."""
    status: str
    service: str
    version: str