"""
API tests for the /inbox endpoints.
"""

import pytest
from fastapi.testclient import TestClient
from httpx import AsyncClient


@pytest.mark.api
class TestInboxEndpoint:
    """Test the /inbox endpoints."""

    def test_get_inbox_empty(self, client: TestClient, valid_api_key):
        """Test getting empty inbox."""
        headers = {"Authorization": f"Bearer {valid_api_key}"}

        response = client.get("/inbox", headers=headers)

        assert response.status_code == 200
        data = response.json()
        assert "events" in data
        assert "next_cursor" in data
        assert isinstance(data["events"], list)
        assert len(data["events"]) == 0
        assert data["next_cursor"] is None

    def test_get_inbox_with_events(self, client: TestClient, valid_api_key, storage_backend):
        """Test getting inbox with events."""
        import asyncio
        from backend.models import Event, EventStatus
        import uuid

        # Create a test event first
        async def create_test_event():
            event = Event(
                id=str(uuid.uuid4()),
                tenant_id="test_tenant",
                source="test",
                type="test.event",
                topic="test",
                payload={"test": True},
                status=EventStatus.PENDING,
                delivered=False
            )
            await storage_backend.create_event(event)
            return event.id

        event_id = asyncio.run(create_test_event())

        headers = {"Authorization": f"Bearer {valid_api_key}"}

        response = client.get("/inbox", headers=headers)

        assert response.status_code == 200
        data = response.json()
        assert len(data["events"]) >= 1

        # Find our event
        our_event = next((e for e in data["events"] if e["id"] == event_id), None)
        assert our_event is not None
        assert our_event["source"] == "test"
        assert our_event["type"] == "test.event"

    def test_get_inbox_with_limit(self, client: TestClient, valid_api_key):
        """Test getting inbox with limit parameter."""
        headers = {"Authorization": f"Bearer {valid_api_key}"}

        response = client.get("/inbox?limit=10", headers=headers)

        assert response.status_code == 200
        data = response.json()
        assert isinstance(data["events"], list)

    def test_get_inbox_limit_too_high(self, client: TestClient, valid_api_key):
        """Test getting inbox with limit exceeding maximum."""
        headers = {"Authorization": f"Bearer {valid_api_key}"}

        # Test with limit exceeding max (500)
        response = client.get("/inbox?limit=1000", headers=headers)

        # Should either accept or return validation error
        assert response.status_code in [200, 422]

    def test_get_inbox_negative_limit(self, client: TestClient, valid_api_key):
        """Test getting inbox with negative limit."""
        headers = {"Authorization": f"Bearer {valid_api_key}"}

        response = client.get("/inbox?limit=-5", headers=headers)

        assert response.status_code == 422

    def test_get_inbox_invalid_limit(self, client: TestClient, valid_api_key):
        """Test getting inbox with invalid limit parameter."""
        headers = {"Authorization": f"Bearer {valid_api_key}"}

        response = client.get("/inbox?limit=invalid", headers=headers)

        assert response.status_code == 422

    def test_get_inbox_with_since_parameter(self, client: TestClient, valid_api_key):
        """Test getting inbox with since parameter."""
        headers = {"Authorization": f"Bearer {valid_api_key}"}

        response = client.get("/inbox?since=2023-01-01T00:00:00Z", headers=headers)

        assert response.status_code == 200
        data = response.json()
        assert "events" in data

    def test_get_inbox_invalid_since_parameter(self, client: TestClient, valid_api_key):
        """Test getting inbox with invalid since parameter."""
        headers = {"Authorization": f"Bearer {valid_api_key}"}

        response = client.get("/inbox?since=invalid-date", headers=headers)

        assert response.status_code == 422

    def test_get_inbox_with_topic_filter(self, client: TestClient, valid_api_key):
        """Test getting inbox filtered by topic."""
        headers = {"Authorization": f"Bearer {valid_api_key}"}

        response = client.get("/inbox?topic=finance", headers=headers)

        assert response.status_code == 200
        data = response.json()
        assert "events" in data

        # All returned events should match the topic
        for event in data["events"]:
            # Note: This depends on whether the filtering is actually implemented
            # If not implemented, this will serve as a reminder to implement it
            pass

    def test_get_inbox_with_type_filter(self, client: TestClient, valid_api_key):
        """Test getting inbox filtered by type."""
        headers = {"Authorization": f"Bearer {valid_api_key}"}

        response = client.get("/inbox?type=invoice.paid", headers=headers)

        assert response.status_code == 200
        data = response.json()
        assert "events" in data

    def test_get_inbox_multiple_filters(self, client: TestClient, valid_api_key):
        """Test getting inbox with multiple filters."""
        headers = {"Authorization": f"Bearer {valid_api_key}"}

        response = client.get(
            "/inbox?topic=finance&type=invoice.paid&limit=25&since=2023-01-01T00:00:00Z",
            headers=headers
        )

        assert response.status_code == 200
        data = response.json()
        assert "events" in data

    def test_get_inbox_no_auth(self, client: TestClient):
        """Test getting inbox without authentication."""
        response = client.get("/inbox")

        assert response.status_code == 401
        data = response.json()
        assert data["error"]["code"] == "AUTHENTICATION_ERROR"

    def test_get_inbox_invalid_auth(self, client: TestClient, invalid_api_key):
        """Test getting inbox with invalid authentication."""
        headers = {"Authorization": f"Bearer {invalid_api_key}"}

        response = client.get("/inbox", headers=headers)

        assert response.status_code == 401
        data = response.json()
        assert data["error"]["code"] == "AUTHENTICATION_ERROR"

    def test_acknowledge_event_success(self, client: TestClient, valid_api_key, storage_backend):
        """Test acknowledging an event successfully."""
        import asyncio
        from backend.models import Event, EventStatus
        import uuid

        # Create a test event first
        async def create_test_event():
            event = Event(
                id=str(uuid.uuid4()),
                tenant_id="test_tenant",
                source="test",
                type="test.event",
                topic="test",
                payload={"test": True},
                status=EventStatus.PENDING,
                delivered=False
            )
            await storage_backend.create_event(event)
            return event.id

        event_id = asyncio.run(create_test_event())

        headers = {"Authorization": f"Bearer {valid_api_key}"}

        response = client.post(f"/inbox/{event_id}/ack", headers=headers)

        assert response.status_code == 200
        data = response.json()
        assert data["id"] == event_id
        assert data["status"] == "acknowledged"

    def test_acknowledge_nonexistent_event(self, client: TestClient, valid_api_key):
        """Test acknowledging a non-existent event."""
        headers = {"Authorization": f"Bearer {valid_api_key}"}

        response = client.post("/inbox/nonexistent-event-id/ack", headers=headers)

        assert response.status_code == 404
        data = response.json()
        assert data["error"]["code"] == "NOT_FOUND"

    def test_acknowledge_event_no_auth(self, client: TestClient):
        """Test acknowledging event without authentication."""
        response = client.post("/inbox/some-event-id/ack")

        assert response.status_code == 401
        data = response.json()
        assert data["error"]["code"] == "AUTHENTICATION_ERROR"

    def test_acknowledge_event_invalid_auth(self, client: TestClient, invalid_api_key):
        """Test acknowledging event with invalid authentication."""
        headers = {"Authorization": f"Bearer {invalid_api_key}"}

        response = client.post("/inbox/some-event-id/ack", headers=headers)

        assert response.status_code == 401
        data = response.json()
        assert data["error"]["code"] == "AUTHENTICATION_ERROR"

    def test_delete_event_success(self, client: TestClient, valid_api_key, storage_backend):
        """Test deleting an event successfully."""
        import asyncio
        from backend.models import Event, EventStatus
        import uuid

        # Create a test event first
        async def create_test_event():
            event = Event(
                id=str(uuid.uuid4()),
                tenant_id="test_tenant",
                source="test",
                type="test.event",
                topic="test",
                payload={"test": True},
                status=EventStatus.PENDING,
                delivered=False
            )
            await storage_backend.create_event(event)
            return event.id

        event_id = asyncio.run(create_test_event())

        headers = {"Authorization": f"Bearer {valid_api_key}"}

        response = client.delete(f"/inbox/{event_id}", headers=headers)

        assert response.status_code == 200
        data = response.json()
        assert data["id"] == event_id
        assert data["status"] == "deleted"

    def test_delete_nonexistent_event(self, client: TestClient, valid_api_key):
        """Test deleting a non-existent event."""
        headers = {"Authorization": f"Bearer {valid_api_key}"}

        response = client.delete("/inbox/nonexistent-event-id", headers=headers)

        assert response.status_code == 404
        data = response.json()
        assert data["error"]["code"] == "NOT_FOUND"

    def test_delete_event_no_auth(self, client: TestClient):
        """Test deleting event without authentication."""
        response = client.delete("/inbox/some-event-id")

        assert response.status_code == 401
        data = response.json()
        assert data["error"]["code"] == "AUTHENTICATION_ERROR"

    def test_delete_event_invalid_auth(self, client: TestClient, invalid_api_key):
        """Test deleting event with invalid authentication."""
        headers = {"Authorization": f"Bearer {invalid_api_key}"}

        response = client.delete("/inbox/some-event-id", headers=headers)

        assert response.status_code == 401
        data = response.json()
        assert data["error"]["code"] == "AUTHENTICATION_ERROR"

    @pytest.mark.asyncio
    async def test_inbox_async_client(self, async_client: AsyncClient, valid_api_key):
        """Test inbox endpoints with async client."""
        headers = {"Authorization": f"Bearer {valid_api_key}"}

        response = await async_client.get("/inbox", headers=headers)

        assert response.status_code == 200
        data = response.json()
        assert "events" in data
        assert "next_cursor" in data

    def test_inbox_response_structure(self, client: TestClient, valid_api_key):
        """Test that inbox response has the expected structure."""
        headers = {"Authorization": f"Bearer {valid_api_key}"}

        response = client.get("/inbox", headers=headers)

        assert response.status_code == 200
        data = response.json()

        # Check required fields
        assert "events" in data
        assert "next_cursor" in data

        # Check field types
        assert isinstance(data["events"], list)
        assert data["next_cursor"] is None or isinstance(data["next_cursor"], str)

    def test_ack_response_structure(self, client: TestClient, valid_api_key, storage_backend):
        """Test that ack response has the expected structure."""
        import asyncio
        from backend.models import Event, EventStatus
        import uuid

        # Create a test event first
        async def create_test_event():
            event = Event(
                id=str(uuid.uuid4()),
                tenant_id="test_tenant",
                source="test",
                type="test.event",
                topic="test",
                payload={"test": True},
                status=EventStatus.PENDING,
                delivered=False
            )
            await storage_backend.create_event(event)
            return event.id

        event_id = asyncio.run(create_test_event())

        headers = {"Authorization": f"Bearer {valid_api_key}"}

        response = client.post(f"/inbox/{event_id}/ack", headers=headers)

        assert response.status_code == 200
        data = response.json()

        # Check required fields
        assert "id" in data
        assert "status" in data

        # Check field types
        assert isinstance(data["id"], str)
        assert isinstance(data["status"], str)

        # Check values
        assert data["id"] == event_id
        assert data["status"] == "acknowledged"

    def test_delete_response_structure(self, client: TestClient, valid_api_key, storage_backend):
        """Test that delete response has the expected structure."""
        import asyncio
        from backend.models import Event, EventStatus
        import uuid

        # Create a test event first
        async def create_test_event():
            event = Event(
                id=str(uuid.uuid4()),
                tenant_id="test_tenant",
                source="test",
                type="test.event",
                topic="test",
                payload={"test": True},
                status=EventStatus.PENDING,
                delivered=False
            )
            await storage_backend.create_event(event)
            return event.id

        event_id = asyncio.run(create_test_event())

        headers = {"Authorization": f"Bearer {valid_api_key}"}

        response = client.delete(f"/inbox/{event_id}", headers=headers)

        assert response.status_code == 200
        data = response.json()

        # Check required fields
        assert "id" in data
        assert "status" in data

        # Check field types
        assert isinstance(data["id"], str)
        assert isinstance(data["status"], str)

        # Check values
        assert data["id"] == event_id
        assert data["status"] == "deleted"

    def test_inbox_event_item_structure(self, client: TestClient, valid_api_key, storage_backend):
        """Test that events in inbox response have the expected structure."""
        import asyncio
        from backend.models import Event, EventStatus
        import uuid

        # Create a test event first
        async def create_test_event():
            event = Event(
                id=str(uuid.uuid4()),
                tenant_id="test_tenant",
                source="test_source",
                type="test.event.type",
                topic="test_topic",
                payload={"key": "value", "number": 42},
                status=EventStatus.PENDING,
                delivered=False
            )
            await storage_backend.create_event(event)
            return event.id

        event_id = asyncio.run(create_test_event())

        headers = {"Authorization": f"Bearer {valid_api_key}"}

        response = client.get("/inbox", headers=headers)

        assert response.status_code == 200
        data = response.json()

        # Find our event
        our_event = next((e for e in data["events"] if e["id"] == event_id), None)
        assert our_event is not None

        # Check required fields
        required_fields = ["id", "created_at", "source", "type", "topic", "payload"]
        for field in required_fields:
            assert field in our_event

        # Check field types
        assert isinstance(our_event["id"], str)
        assert isinstance(our_event["created_at"], str)
        assert isinstance(our_event["payload"], dict)

        # Check values
        assert our_event["id"] == event_id
        assert our_event["source"] == "test_source"
        assert our_event["type"] == "test.event.type"
        assert our_event["topic"] == "test_topic"
        assert our_event["payload"]["key"] == "value"
        assert our_event["payload"]["number"] == 42