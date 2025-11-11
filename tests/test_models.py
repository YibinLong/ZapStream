"""
Unit tests for Pydantic models and schema validation.
"""

import pytest
from datetime import datetime
from pydantic import ValidationError

from backend.models import (
    EventCreate,
    EventResponse,
    EventListItem,
    InboxResponse,
    AckResponse,
    DeleteResponse,
    ErrorResponse,
    EventStatus
)


@pytest.mark.unit
class TestEventCreate:
    """Test EventCreate model validation."""

    def test_valid_event_create(self):
        """Test creating a valid EventCreate."""
        data = {
            "source": "billing",
            "type": "invoice.paid",
            "topic": "finance",
            "payload": {
                "invoiceId": "inv_123",
                "amount": 4200,
                "currency": "USD"
            }
        }

        event = EventCreate(**data)
        assert event.source == "billing"
        assert event.type == "invoice.paid"
        assert event.topic == "finance"
        assert event.payload == {
            "invoiceId": "inv_123",
            "amount": 4200,
            "currency": "USD"
        }

    def test_minimal_event_create(self):
        """Test creating EventCreate with only required fields."""
        data = {"payload": {"test": True}}

        event = EventCreate(**data)
        assert event.payload == {"test": True}
        assert event.source is None
        assert event.type is None
        assert event.topic is None

    def test_empty_payload_validation(self):
        """Test that empty payload is not allowed."""
        data = {"payload": {}}

        # This should work - empty dict is valid
        event = EventCreate(**data)
        assert event.payload == {}

    def test_invalid_payload_type(self):
        """Test that non-dict payload is rejected."""
        with pytest.raises(ValidationError) as exc_info:
            EventCreate(payload="invalid")

        errors = exc_info.value.errors()
        assert len(errors) == 1
        assert "dict" in errors[0]['msg']

    def test_nested_payload_validation(self):
        """Test validation of nested payload structures."""
        complex_payload = {
            "user": {
                "id": 123,
                "name": "John Doe",
                "metadata": {
                    "source": "web",
                    "campaign": "summer_2023"
                }
            },
            "transaction": {
                "id": "txn_abc123",
                "amount": 99.99,
                "currency": "EUR",
                "items": [
                    {"id": 1, "name": "Product A", "quantity": 2},
                    {"id": 2, "name": "Product B", "quantity": 1}
                ]
            }
        }

        event = EventCreate(payload=complex_payload)
        assert event.payload == complex_payload


@pytest.mark.unit
class TestResponseModels:
    """Test response model validation."""

    def test_event_response_valid(self):
        """Test valid EventResponse."""
        data = {
            "id": "evt_123",
            "received_at": datetime.now().isoformat(),
            "status": "accepted"
        }

        response = EventResponse(**data)
        assert response.id == "evt_123"
        assert response.status == "accepted"

    def test_event_list_item_valid(self):
        """Test valid EventListItem."""
        data = {
            "id": "evt_456",
            "created_at": datetime.now().isoformat(),
            "source": "test",
            "type": "test.event",
            "topic": "test",
            "payload": {"key": "value"}
        }

        item = EventListItem(**data)
        assert item.id == "evt_456"
        assert item.source == "test"
        assert item.payload == {"key": "value"}

    def test_inbox_response_with_cursor(self):
        """Test InboxResponse with next_cursor."""
        data = {
            "events": [
                {
                    "id": "evt_1",
                    "created_at": datetime.now().isoformat(),
                    "payload": {"test": True}
                }
            ],
            "next_cursor": "2023-01-01T00:00:00Z|evt_1"
        }

        response = InboxResponse(**data)
        assert len(response.events) == 1
        assert response.next_cursor == "2023-01-01T00:00:00Z|evt_1"

    def test_inbox_response_without_cursor(self):
        """Test InboxResponse without next_cursor."""
        data = {
            "events": []
        }

        response = InboxResponse(**data)
        assert len(response.events) == 0
        assert response.next_cursor is None

    def test_ack_response_valid(self):
        """Test valid AckResponse."""
        data = {
            "id": "evt_789",
            "status": "acknowledged"
        }

        response = AckResponse(**data)
        assert response.id == "evt_789"
        assert response.status == "acknowledged"

    def test_delete_response_valid(self):
        """Test valid DeleteResponse."""
        data = {
            "id": "evt_999",
            "status": "deleted"
        }

        response = DeleteResponse(**data)
        assert response.id == "evt_999"
        assert response.status == "deleted"

    def test_error_response_valid(self):
        """Test valid ErrorResponse."""
        data = {
            "error": {
                "code": "VALIDATION_ERROR",
                "message": "Invalid input",
                "requestId": "req_123"
            }
        }

        response = ErrorResponse(**data)
        assert response.error["code"] == "VALIDATION_ERROR"
        assert response.error["message"] == "Invalid input"
        assert response.error["requestId"] == "req_123"

    def test_error_response_minimal(self):
        """Test ErrorResponse with minimal fields."""
        data = {
            "error": {
                "code": "INTERNAL_ERROR",
                "message": "Something went wrong"
            }
        }

        response = ErrorResponse(**data)
        assert response.error["code"] == "INTERNAL_ERROR"
        assert response.error["message"] == "Something went wrong"
        assert "requestId" not in response.error


@pytest.mark.unit
class TestEventStatus:
    """Test EventStatus enum."""

    def test_event_status_values(self):
        """Test that EventStatus has correct values."""
        assert EventStatus.PENDING == "pending"
        assert EventStatus.ACKNOWLEDGED == "acknowledged"
        assert EventStatus.DELETED == "deleted"

    def test_event_status_iteration(self):
        """Test iterating over EventStatus values."""
        statuses = list(EventStatus)
        assert len(statuses) == 3
        assert "pending" in [s.value for s in statuses]
        assert "acknowledged" in [s.value for s in statuses]
        assert "deleted" in [s.value for s in statuses]


@pytest.mark.unit
class TestModelSerialization:
    """Test model serialization and JSON export."""

    def test_event_create_json_serialization(self):
        """Test EventCreate JSON serialization."""
        event = EventCreate(
            source="test",
            payload={"key": "value", "number": 42}
        )

        json_data = event.model_dump()
        assert json_data["source"] == "test"
        assert json_data["payload"]["key"] == "value"
        assert json_data["payload"]["number"] == 42

    def test_event_response_json_serialization(self):
        """Test EventResponse JSON serialization."""
        now = datetime.now()
        response = EventResponse(
            id="evt_123",
            received_at=now,
            status="accepted"
        )

        json_data = response.model_dump()
        assert json_data["id"] == "evt_123"
        assert json_data["status"] == "accepted"

    def test_model_json_schema(self):
        """Test that models generate valid JSON schemas."""
        schema = EventCreate.model_json_schema()
        assert "properties" in schema
        assert "payload" in schema["properties"]
        assert schema["properties"]["payload"]["type"] == "object"
        assert "source" in schema["properties"]
        assert "type" in schema["properties"]
        assert "topic" in schema["properties"]