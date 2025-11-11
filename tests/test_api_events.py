"""
API tests for the /events endpoint.
"""

import pytest
import json
from datetime import datetime
from fastapi.testclient import TestClient
from httpx import AsyncClient


@pytest.mark.api
class TestEventsEndpoint:
    """Test the /events endpoint."""

    def test_create_event_success_bearer_auth(self, client: TestClient, sample_event_payload, valid_api_key):
        """Test successful event creation with Bearer token."""
        headers = {
            "Authorization": f"Bearer {valid_api_key}",
            "Content-Type": "application/json"
        }

        response = client.post("/events", json=sample_event_payload, headers=headers)

        assert response.status_code == 200
        data = response.json()
        assert "id" in data
        assert "received_at" in data
        assert data["status"] == "accepted"

        # Verify request ID is returned
        assert "x-request-id" in response.headers

    def test_create_event_success_x_api_key(self, client: TestClient, sample_event_payload, valid_api_key):
        """Test successful event creation with X-API-Key header."""
        headers = {
            "X-API-Key": valid_api_key,
            "Content-Type": "application/json"
        }

        response = client.post("/events", json=sample_event_payload, headers=headers)

        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "accepted"

    def test_create_event_minimal_payload(self, client: TestClient, valid_api_key):
        """Test creating event with minimal required payload."""
        payload = {"payload": {"test": True}}
        headers = {
            "Authorization": f"Bearer {valid_api_key}",
            "Content-Type": "application/json"
        }

        response = client.post("/events", json=payload, headers=headers)

        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "accepted"

    def test_create_event_with_idempotency_key(self, client: TestClient, sample_event_payload, valid_api_key):
        """Test creating event with idempotency key."""
        headers = {
            "Authorization": f"Bearer {valid_api_key}",
            "Content-Type": "application/json",
            "X-Idempotency-Key": "unique-key-123"
        }

        # First request
        response1 = client.post("/events", json=sample_event_payload, headers=headers)
        assert response1.status_code == 200
        data1 = response1.json()
        event_id_1 = data1["id"]

        # Second request with same idempotency key
        response2 = client.post("/events", json=sample_event_payload, headers=headers)
        assert response2.status_code == 409  # Conflict for duplicate idempotency key

        data2 = response2.json()
        assert data2["error"]["code"] == "CONFLICT"

    def test_create_event_different_idempotency_keys(self, client: TestClient, sample_event_payload, valid_api_key):
        """Test creating events with different idempotency keys."""
        headers1 = {
            "Authorization": f"Bearer {valid_api_key}",
            "Content-Type": "application/json",
            "X-Idempotency-Key": "key-1"
        }

        headers2 = {
            "Authorization": f"Bearer {valid_api_key}",
            "Content-Type": "application/json",
            "X-Idempotency-Key": "key-2"
        }

        response1 = client.post("/events", json=sample_event_payload, headers=headers1)
        response2 = client.post("/events", json=sample_event_payload, headers=headers2)

        assert response1.status_code == 200
        assert response2.status_code == 200

        # Should create different events
        assert response1.json()["id"] != response2.json()["id"]

    def test_create_event_no_auth(self, client: TestClient, sample_event_payload):
        """Test creating event without authentication."""
        headers = {"Content-Type": "application/json"}

        response = client.post("/events", json=sample_event_payload, headers=headers)

        assert response.status_code == 401
        data = response.json()
        assert data["error"]["code"] == "AUTHENTICATION_ERROR"

    def test_create_event_invalid_auth(self, client: TestClient, sample_event_payload, invalid_api_key):
        """Test creating event with invalid authentication."""
        headers = {
            "Authorization": f"Bearer {invalid_api_key}",
            "Content-Type": "application/json"
        }

        response = client.post("/events", json=sample_event_payload, headers=headers)

        assert response.status_code == 401
        data = response.json()
        assert data["error"]["code"] == "AUTHENTICATION_ERROR"

    def test_create_event_invalid_json(self, client: TestClient, valid_api_key):
        """Test creating event with invalid JSON."""
        headers = {
            "Authorization": f"Bearer {valid_api_key}",
            "Content-Type": "application/json"
        }

        # Invalid JSON (missing closing brace)
        response = client.post(
            "/events",
            data='{"payload": {"test": true}',
            headers=headers
        )

        assert response.status_code == 422  # Validation error

    def test_create_event_empty_payload(self, client: TestClient, valid_api_key):
        """Test creating event with empty payload."""
        headers = {
            "Authorization": f"Bearer {valid_api_key}",
            "Content-Type": "application/json"
        }

        response = client.post("/events", json={}, headers=headers)

        assert response.status_code == 422  # Validation error for missing payload

    def test_create_event_non_object_payload(self, client: TestClient, valid_api_key):
        """Test creating event with non-object payload."""
        headers = {
            "Authorization": f"Bearer {valid_api_key}",
            "Content-Type": "application/json"
        }

        # Payload as string instead of object
        response = client.post("/events", json={"payload": "not an object"}, headers=headers)

        assert response.status_code == 422

    def test_create_event_large_payload(self, client: TestClient, valid_api_key):
        """Test creating event with payload exceeding size limit."""
        # Create a large payload that exceeds the test limit (1024 bytes)
        large_payload = {
            "source": "test",
            "type": "test.large",
            "topic": "test",
            "payload": {"data": "x" * 2000}  # This should exceed the limit
        }

        headers = {
            "Authorization": f"Bearer {valid_api_key}",
            "Content-Type": "application/json"
        }

        response = client.post("/events", json=large_payload, headers=headers)

        assert response.status_code == 400
        data = response.json()
        assert data["error"]["code"] == "VALIDATION_ERROR"
        assert "payload" in data["error"]["message"].lower()

    def test_create_event_wrong_content_type(self, client: TestClient, sample_event_payload, valid_api_key):
        """Test creating event with wrong content type."""
        headers = {
            "Authorization": f"Bearer {valid_api_key}",
            "Content-Type": "text/plain"
        }

        response = client.post("/events", data=json.dumps(sample_event_payload), headers=headers)

        # FastAPI should still handle this as JSON if it can parse it
        assert response.status_code in [200, 415]  # Either accepts or rejects content type

    @pytest.mark.asyncio
    async def test_create_event_async_client(self, async_client: AsyncClient, sample_event_payload, valid_api_key):
        """Test creating event with async client."""
        headers = {
            "Authorization": f"Bearer {valid_api_key}",
            "Content-Type": "application/json"
        }

        response = await async_client.post("/events", json=sample_event_payload, headers=headers)

        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "accepted"

    def test_create_event_complex_payload(self, client: TestClient, valid_api_key):
        """Test creating event with complex nested payload."""
        complex_payload = {
            "source": "order_system",
            "type": "order.created",
            "topic": "ecommerce",
            "payload": {
                "order_id": "ord_abc123",
                "customer": {
                    "id": 12345,
                    "name": "John Doe",
                    "email": "john@example.com",
                    "addresses": [
                        {
                            "type": "shipping",
                            "street": "123 Main St",
                            "city": "Anytown",
                            "country": "US",
                            "postal_code": "12345"
                        }
                    ]
                },
                "items": [
                    {
                        "product_id": "prod_001",
                        "name": "Widget",
                        "quantity": 2,
                        "unit_price": 19.99,
                        "total": 39.98
                    },
                    {
                        "product_id": "prod_002",
                        "name": "Gadget",
                        "quantity": 1,
                        "unit_price": 29.99,
                        "total": 29.99
                    }
                ],
                "totals": {
                    "subtotal": 69.97,
                    "tax": 7.00,
                    "shipping": 5.99,
                    "total": 82.96
                },
                "metadata": {
                    "source": "web",
                    "campaign": "summer_sale",
                    "utm_parameters": {
                        "source": "google",
                        "medium": "cpc",
                        "campaign": "summer_sale"
                    }
                }
            }
        }

        headers = {
            "Authorization": f"Bearer {valid_api_key}",
            "Content-Type": "application/json"
        }

        response = client.post("/events", json=complex_payload, headers=headers)

        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "accepted"

    def test_create_event_unicode_payload(self, client: TestClient, valid_api_key):
        """Test creating event with Unicode characters in payload."""
        unicode_payload = {
            "source": "国际系统",
            "type": "用户.创建",
            "topic": "用户管理",
            "payload": {
                "用户名": "张三",
                "邮箱": "zhangsan@example.com",
                "消息": "Hello 世界! 🌍",
                "特殊字符": "ñáéíóú ß",
                "emoji": "🎉🚀💻"
            }
        }

        headers = {
            "Authorization": f"Bearer {valid_api_key}",
            "Content-Type": "application/json"
        }

        response = client.post("/events", json=unicode_payload, headers=headers)

        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "accepted"

    def test_create_event_special_characters_in_key(self, client: TestClient, valid_api_key):
        """Test idempotency key with special characters."""
        special_key = "key-with.special_chars@123#%&"

        headers = {
            "Authorization": f"Bearer {valid_api_key}",
            "Content-Type": "application/json",
            "X-Idempotency-Key": special_key
        }

        payload = {"payload": {"test": True}}

        response = client.post("/events", json=payload, headers=headers)

        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "accepted"

    def test_create_event_response_structure(self, client: TestClient, sample_event_payload, valid_api_key):
        """Test that response has the expected structure."""
        headers = {
            "Authorization": f"Bearer {valid_api_key}",
            "Content-Type": "application/json"
        }

        response = client.post("/events", json=sample_event_payload, headers=headers)

        assert response.status_code == 200
        data = response.json()

        # Check required fields
        assert "id" in data
        assert "received_at" in data
        assert "status" in data

        # Check field types
        assert isinstance(data["id"], str)
        assert isinstance(data["received_at"], str)
        assert isinstance(data["status"], str)

        # Check values
        assert data["status"] == "accepted"
        assert len(data["id"]) > 0

        # Check that received_at is a valid ISO datetime
        try:
            datetime.fromisoformat(data["received_at"].replace('Z', '+00:00'))
        except ValueError:
            pytest.fail("received_at is not a valid ISO datetime")

    def test_event_id_generation(self, client: TestClient, sample_event_payload, valid_api_key):
        """Test that different events get different IDs."""
        headers = {
            "Authorization": f"Bearer {valid_api_key}",
            "Content-Type": "application/json"
        }

        # Create multiple events
        event_ids = []
        for i in range(5):
            # Modify payload slightly to ensure different events
            payload = sample_event_payload.copy()
            payload["payload"]["sequence"] = i

            response = client.post("/events", json=payload, headers=headers)
            assert response.status_code == 200
            event_ids.append(response.json()["id"])

        # All IDs should be unique
        assert len(set(event_ids)) == len(event_ids)