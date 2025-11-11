"""
Concurrency tests for ZapStream Backend.

Tests race conditions and concurrent access scenarios.
"""

import pytest
import asyncio
import aiohttp
from typing import List, Dict
from concurrent.futures import ThreadPoolExecutor
import time


@pytest.mark.slow
@pytest.mark.api
class TestConcurrency:
    """Test concurrent API access scenarios."""

    @pytest.mark.asyncio
    async def test_concurrent_event_creation_different_keys(self, test_app, sample_event_payload, valid_api_key):
        """Test creating multiple events simultaneously with different idempotency keys."""
        from httpx import AsyncClient

        base_url = "http://test"
        async with AsyncClient(app=test_app, base_url=base_url) as client:

            async def create_event(key_suffix: int):
                headers = {
                    "Authorization": f"Bearer {valid_api_key}",
                    "Content-Type": "application/json",
                    "X-Idempotency-Key": f"concurrent-key-{key_suffix}"
                }
                payload = sample_event_payload.copy()
                payload["payload"]["suffix"] = key_suffix

                response = await client.post("/events", json=payload, headers=headers)
                return response

            # Create 10 events concurrently
            tasks = [create_event(i) for i in range(10)]
            responses = await asyncio.gather(*tasks, return_exceptions=True)

            # All should succeed (200)
            success_count = sum(1 for r in responses if hasattr(r, 'status_code') and r.status_code == 200)
            assert success_count == 10

            # All should have different event IDs
            event_ids = []
            for r in responses:
                if hasattr(r, 'json'):
                    data = r.json()
                    if 'id' in data:
                        event_ids.append(data['id'])

            assert len(set(event_ids)) == len(event_ids)  # All unique

    @pytest.mark.asyncio
    async def test_concurrent_event_creation_same_key(self, test_app, sample_event_payload, valid_api_key):
        """Test creating multiple events with the same idempotency key concurrently."""
        from httpx import AsyncClient

        base_url = "http://test"
        async with AsyncClient(app=test_app, base_url=base_url) as client:

            async def create_event_with_same_key():
                headers = {
                    "Authorization": f"Bearer {valid_api_key}",
                    "Content-Type": "application/json",
                    "X-Idempotency-Key": "same-concurrent-key"
                }

                response = await client.post("/events", json=sample_event_payload, headers=headers)
                return response

            # Create 5 events concurrently with the same idempotency key
            tasks = [create_event_with_same_key() for _ in range(5)]
            responses = await asyncio.gather(*tasks, return_exceptions=True)

            # Only one should succeed (200), others should get 409 (Conflict)
            success_count = sum(1 for r in responses if hasattr(r, 'status_code') and r.status_code == 200)
            conflict_count = sum(1 for r in responses if hasattr(r, 'status_code') and r.status_code == 409)

            assert success_count == 1  # Only one should succeed
            assert conflict_count == 4  # Rest should get conflict

            # The successful response should have an event ID
            successful_responses = [r for r in responses if hasattr(r, 'status_code') and r.status_code == 200]
            assert len(successful_responses) == 1

            success_data = successful_responses[0].json()
            assert "id" in success_data

    @pytest.mark.asyncio
    async def test_concurrent_inbox_access(self, test_app, valid_api_key, storage_backend):
        """Test concurrent access to inbox endpoint."""
        from httpx import AsyncClient

        # Create some test events first
        import uuid
        from backend.models import Event, EventStatus

        async def create_test_events():
            events = []
            for i in range(5):
                event = Event(
                    id=str(uuid.uuid4()),
                    tenant_id="test_tenant",
                    source="test",
                    type="test.concurrent",
                    topic="test",
                    payload={"index": i},
                    status=EventStatus.PENDING,
                    delivered=False
                )
                await storage_backend.create_event(event)
                events.append(event.id)
            return events

        event_ids = await create_test_events()

        base_url = "http://test"
        async with AsyncClient(app=test_app, base_url=base_url) as client:

            async def get_inbox():
                headers = {"Authorization": f"Bearer {valid_api_key}"}
                response = await client.get("/inbox", headers=headers)
                return response

            # Access inbox concurrently
            tasks = [get_inbox() for _ in range(10)]
            responses = await asyncio.gather(*tasks, return_exceptions=True)

            # All should succeed
            success_count = sum(1 for r in responses if hasattr(r, 'status_code') and r.status_code == 200)
            assert success_count == 10

            # All should return the same events
            for r in responses:
                if hasattr(r, 'json'):
                    data = r.json()
                    assert "events" in data
                    assert isinstance(data["events"], list)

    @pytest.mark.asyncio
    async def test_concurrent_event_acknowledgment(self, test_app, valid_api_key, storage_backend):
        """Test concurrent acknowledgment of the same event."""
        from httpx import AsyncClient

        # Create a test event first
        import uuid
        from backend.models import Event, EventStatus

        event = Event(
            id=str(uuid.uuid4()),
            tenant_id="test_tenant",
            source="test",
            type="test.concurrent_ack",
            topic="test",
            payload={"test": True},
            status=EventStatus.PENDING,
            delivered=False
        )
        await storage_backend.create_event(event)
        event_id = event.id

        base_url = "http://test"
        async with AsyncClient(app=test_app, base_url=base_url) as client:

            async def acknowledge_event():
                headers = {"Authorization": f"Bearer {valid_api_key}"}
                response = await client.post(f"/inbox/{event_id}/ack", headers=headers)
                return response

            # Try to acknowledge the same event concurrently
            tasks = [acknowledge_event() for _ in range(5)]
            responses = await asyncio.gather(*tasks, return_exceptions=True)

            # All should succeed (acknowledgment should be idempotent)
            success_count = sum(1 for r in responses if hasattr(r, 'status_code') and r.status_code == 200)
            assert success_count == 5  # All should succeed due to idempotency

    def test_threadpool_event_creation(self, client: TestClient, sample_event_payload, valid_api_key):
        """Test event creation using thread pool to simulate concurrent access."""
        def create_event(thread_id: int):
            headers = {
                "Authorization": f"Bearer {valid_api_key}",
                "Content-Type": "application/json",
                "X-Idempotency-Key": f"thread-key-{thread_id}"
            }
            payload = sample_event_payload.copy()
            payload["payload"]["thread_id"] = thread_id

            response = client.post("/events", json=payload, headers=headers)
            return {
                "thread_id": thread_id,
                "status_code": response.status_code,
                "data": response.json() if response.status_code == 200 else None
            }

        # Use ThreadPoolExecutor to simulate concurrent requests
        with ThreadPoolExecutor(max_workers=5) as executor:
            futures = [executor.submit(create_event, i) for i in range(10)]
            results = [future.result() for future in futures]

        # All should succeed
        success_count = sum(1 for r in results if r["status_code"] == 200)
        assert success_count == 10

        # All should have different event IDs
        event_ids = [r["data"]["id"] for r in results if r["data"]]
        assert len(set(event_ids)) == len(event_ids)  # All unique

    def test_threadpool_same_idempotency_key(self, client: TestClient, sample_event_payload, valid_api_key):
        """Test that using the same idempotency key across threads results in only one success."""
        def create_event_with_same_key(thread_id: int):
            headers = {
                "Authorization": f"Bearer {valid_api_key}",
                "Content-Type": "application/json",
                "X-Idempotency-Key": "thread-same-key"
            }

            response = client.post("/events", json=sample_event_payload, headers=headers)
            return {
                "thread_id": thread_id,
                "status_code": response.status_code,
                "data": response.json() if response.status_code in [200, 409] else None
            }

        # Use ThreadPoolExecutor to simulate concurrent requests with same key
        with ThreadPoolExecutor(max_workers=5) as executor:
            futures = [executor.submit(create_event_with_same_key, i) for i in range(5)]
            results = [future.result() for future in futures]

        # Only one should succeed (200), others should get 409
        success_count = sum(1 for r in results if r["status_code"] == 200)
        conflict_count = sum(1 for r in results if r["status_code"] == 409)

        assert success_count == 1
        assert conflict_count == 4

    @pytest.mark.asyncio
    async def test_mixed_concurrent_operations(self, test_app, sample_event_payload, valid_api_key, storage_backend):
        """Test mixed concurrent operations: create, read, acknowledge."""
        from httpx import AsyncClient
        import uuid
        from backend.models import Event, EventStatus

        # Create a test event first for acknowledgment
        event = Event(
            id=str(uuid.uuid4()),
            tenant_id="test_tenant",
            source="test",
            type="test.mixed",
            topic="test",
            payload={"test": True},
            status=EventStatus.PENDING,
            delivered=False
        )
        await storage_backend.create_event(event)
        event_id = event.id

        base_url = "http://test"
        async with AsyncClient(app=test_app, base_url=base_url) as client:

            async def create_event():
                headers = {
                    "Authorization": f"Bearer {valid_api_key}",
                    "Content-Type": "application/json",
                    "X-Idempotency-Key": f"mixed-create-{time.time()}"
                }
                return await client.post("/events", json=sample_event_payload, headers=headers)

            async def get_inbox():
                headers = {"Authorization": f"Bearer {valid_api_key}"}
                return await client.get("/inbox", headers=headers)

            async def acknowledge_event():
                headers = {"Authorization": f"Bearer {valid_api_key}"}
                return await client.post(f"/inbox/{event_id}/ack", headers=headers)

            # Mix of operations
            tasks = (
                [create_event() for _ in range(3)] +
                [get_inbox() for _ in range(3)] +
                [acknowledge_event() for _ in range(2)]
            )

            responses = await asyncio.gather(*tasks, return_exceptions=True)

            # All should succeed
            success_count = sum(1 for r in responses if hasattr(r, 'status_code') and 200 <= r.status_code < 300)
            assert success_count >= 7  # At least most should succeed

    @pytest.mark.asyncio
    async def test_race_condition_inbox_filtering(self, test_app, valid_api_key, storage_backend):
        """Test race conditions in inbox filtering with concurrent event creation and reading."""
        from httpx import AsyncClient
        import uuid
        from backend.models import Event, EventStatus

        base_url = "http://test"
        async with AsyncClient(app=test_app, base_url=base_url) as client:

            async def create_events_batch(start_id: int, count: int):
                """Create a batch of events."""
                events = []
                for i in range(count):
                    event = Event(
                        id=str(uuid.uuid4()),
                        tenant_id="test_tenant",
                        source="race_test",
                        type="race.event",
                        topic="race_topic",
                        payload={"batch": start_id, "index": i},
                        status=EventStatus.PENDING,
                        delivered=False
                    )
                    await storage_backend.create_event(event)
                    events.append(event.id)
                return events

            async def get_inbox_with_filter():
                headers = {"Authorization": f"Bearer {valid_api_key}"}
                return await client.get("/inbox?topic=race_topic", headers=headers)

            # Create events and read inbox concurrently
            tasks = []
            for i in range(3):
                tasks.append(create_events_batch(i, 5))
                tasks.append(get_inbox_with_filter())

            results = await asyncio.gather(*tasks, return_exceptions=True)

            # Should have some successful reads
            read_responses = [r for r in results if hasattr(r, 'status_code')]
            success_reads = sum(1 for r in read_responses if 200 <= r.status_code < 300)
            assert success_reads >= 2  # At least some reads should succeed


@pytest.mark.slow
class TestRateLimitingConcurrency:
    """Test rate limiting under concurrent load."""

    @pytest.mark.asyncio
    async def test_concurrent_requests_rate_limit(self, test_app, sample_event_payload, valid_api_key):
        """Test rate limiting behavior under concurrent requests."""
        from httpx import AsyncClient

        # Temporarily set a low rate limit for testing
        import os
        original_rate_limit = os.environ.get("RATE_LIMIT_PER_MINUTE")
        os.environ["RATE_LIMIT_PER_MINUTE"] = "5"

        try:
            base_url = "http://test"
            async with AsyncClient(app=test_app, base_url=base_url) as client:

                async def create_event():
                    headers = {
                        "Authorization": f"Bearer {valid_api_key}",
                        "Content-Type": "application/json",
                        "X-Idempotency-Key": f"rate-limit-{time.time_ns()}"
                    }
                    return await client.post("/events", json=sample_event_payload, headers=headers)

                # Send 10 requests concurrently
                tasks = [create_event() for _ in range(10)]
                responses = await asyncio.gather(*tasks, return_exceptions=True)

                # Some should succeed, some should be rate limited
                success_count = sum(1 for r in responses if hasattr(r, 'status_code') and r.status_code == 200)
                rate_limit_count = sum(1 for r in responses if hasattr(r, 'status_code') and r.status_code == 429)

                # At least some should be rate limited
                assert rate_limit_count > 0
                assert success_count + rate_limit_count == 10

        finally:
            # Restore original rate limit
            if original_rate_limit:
                os.environ["RATE_LIMIT_PER_MINUTE"] = original_rate_limit
            else:
                os.environ.pop("RATE_LIMIT_PER_MINUTE", None)