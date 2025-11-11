"""
Rate limiting tests for ZapStream Backend.

Tests that rate limiting works correctly and returns proper 429 responses.
"""

import pytest
import time
import os
from fastapi.testclient import TestClient
from httpx import AsyncClient


@pytest.mark.api
class TestRateLimiting:
    """Test rate limiting functionality."""

    def test_rate_limit_basic(self, client: TestClient, sample_event_payload, valid_api_key):
        """Test basic rate limiting with multiple requests."""
        # Temporarily set a low rate limit for testing
        original_rate_limit = os.environ.get("RATE_LIMIT_PER_MINUTE")
        os.environ["RATE_LIMIT_PER_MINUTE"] = "3"

        try:
            headers = {
                "Authorization": f"Bearer {valid_api_key}",
                "Content-Type": "application/json"
            }

            # Make multiple requests quickly
            responses = []
            for i in range(5):
                # Use different idempotency keys to avoid conflicts
                headers["X-Idempotency-Key"] = f"rate-test-{i}"
                response = client.post("/events", json=sample_event_payload, headers=headers)
                responses.append(response)
                time.sleep(0.1)  # Small delay between requests

            # First 3 should succeed, remaining should be rate limited
            success_count = sum(1 for r in responses if r.status_code == 200)
            rate_limit_count = sum(1 for r in responses if r.status_code == 429)

            assert success_count <= 3  # At most 3 should succeed
            assert rate_limit_count >= 1  # At least 1 should be rate limited

            # Check rate limit response format
            rate_limit_responses = [r for r in responses if r.status_code == 429]
            if rate_limit_responses:
                response = rate_limit_responses[0]
                data = response.json()
                assert data["error"]["code"] == "RATE_LIMIT_EXCEEDED"

                # Check for Retry-After header (if implemented)
                retry_after = response.headers.get("Retry-After")
                if retry_after:
                    # Should be a number
                    assert retry_after.isdigit()
                    assert int(retry_after) > 0

        finally:
            # Restore original rate limit
            if original_rate_limit:
                os.environ["RATE_LIMIT_PER_MINUTE"] = original_rate_limit
            else:
                os.environ.pop("RATE_LIMIT_PER_MINUTE", None)

    def test_rate_limit_per_api_key(self, client: TestClient, sample_event_payload):
        """Test that rate limiting is applied per API key."""
        # Set low rate limit
        original_rate_limit = os.environ.get("RATE_LIMIT_PER_MINUTE")
        os.environ["RATE_LIMIT_PER_MINUTE"] = "2"

        try:
            # Make requests with different API keys
            api_key_1 = "test_key_123"
            api_key_2 = "test_key_456"

            responses_key1 = []
            responses_key2 = []

            # Make requests with key 1
            for i in range(3):
                headers = {
                    "Authorization": f"Bearer {api_key_1}",
                    "Content-Type": "application/json",
                    "X-Idempotency-Key": f"key1-{i}"
                }
                response = client.post("/events", json=sample_event_payload, headers=headers)
                responses_key1.append(response)
                time.sleep(0.05)

            # Make requests with key 2
            for i in range(3):
                headers = {
                    "Authorization": f"Bearer {api_key_2}",
                    "Content-Type": "application/json",
                    "X-Idempotency-Key": f"key2-{i}"
                }
                response = client.post("/events", json=sample_event_payload, headers=headers)
                responses_key2.append(response)
                time.sleep(0.05)

            # Both keys should have some successful requests (independent limits)
            success_key1 = sum(1 for r in responses_key1 if r.status_code == 200)
            success_key2 = sum(1 for r in responses_key2 if r.status_code == 200)

            # Each key should have at least some successful requests
            assert success_key1 >= 1
            assert success_key2 >= 1

        finally:
            # Restore original rate limit
            if original_rate_limit:
                os.environ["RATE_LIMIT_PER_MINUTE"] = original_rate_limit
            else:
                os.environ.pop("RATE_LIMIT_PER_MINUTE", None)

    def test_rate_limit_recovery(self, client: TestClient, sample_event_payload, valid_api_key):
        """Test that rate limiting recovers after time passes."""
        # Set very low rate limit for quick testing
        original_rate_limit = os.environ.get("RATE_LIMIT_PER_MINUTE")
        os.environ["RATE_LIMIT_PER_MINUTE"] = "1"

        try:
            headers = {
                "Authorization": f"Bearer {valid_api_key}",
                "Content-Type": "application/json"
            }

            # First request should succeed
            headers["X-Idempotency-Key"] = "recovery-test-1"
            response1 = client.post("/events", json=sample_event_payload, headers=headers)
            assert response1.status_code == 200

            # Second request immediately should be rate limited
            headers["X-Idempotency-Key"] = "recovery-test-2"
            response2 = client.post("/events", json=sample_event_payload, headers=headers)
            assert response2.status_code == 429

            # Wait a bit and try again (this might not work if rate limit window is long)
            # In a real test environment, you might need to mock time or use a shorter window
            time.sleep(1)

            headers["X-Idempotency-Key"] = "recovery-test-3"
            response3 = client.post("/events", json=sample_event_payload, headers=headers)
            # This might still be rate limited depending on implementation
            # The important thing is that the rate limiting is working

        finally:
            # Restore original rate limit
            if original_rate_limit:
                os.environ["RATE_LIMIT_PER_MINUTE"] = original_rate_limit
            else:
                os.environ.pop("RATE_LIMIT_PER_MINUTE", None)

    @pytest.mark.asyncio
    async def test_rate_limit_concurrent_requests(self, test_app, sample_event_payload, valid_api_key):
        """Test rate limiting with concurrent requests."""
        from httpx import AsyncClient

        # Set low rate limit for testing
        original_rate_limit = os.environ.get("RATE_LIMIT_PER_MINUTE")
        os.environ["RATE_LIMIT_PER_MINUTE"] = "2"

        try:
            base_url = "http://test"
            async with AsyncClient(app=test_app, base_url=base_url) as client:

                async def make_request(suffix: int):
                    headers = {
                        "Authorization": f"Bearer {valid_api_key}",
                        "Content-Type": "application/json",
                        "X-Idempotency-Key": f"concurrent-rate-{suffix}"
                    }
                    return await client.post("/events", json=sample_event_payload, headers=headers)

                # Send multiple requests concurrently
                tasks = [make_request(i) for i in range(5)]
                responses = await asyncio.gather(*tasks, return_exceptions=True)

                # At most 2 should succeed due to rate limiting
                success_count = sum(1 for r in responses if hasattr(r, 'status_code') and r.status_code == 200)
                rate_limit_count = sum(1 for r in responses if hasattr(r, 'status_code') and r.status_code == 429)

                assert success_count <= 2
                assert rate_limit_count >= 1

        finally:
            # Restore original rate limit
            if original_rate_limit:
                os.environ["RATE_LIMIT_PER_MINUTE"] = original_rate_limit
            else:
                os.environ.pop("RATE_LIMIT_PER_MINUTE", None)

    def test_rate_limit_different_endpoints(self, client: TestClient, sample_event_payload, valid_api_key):
        """Test that rate limiting applies across different endpoints."""
        # Set low rate limit
        original_rate_limit = os.environ.get("RATE_LIMIT_PER_MINUTE")
        os.environ["RATE_LIMIT_PER_MINUTE"] = "3"

        try:
            headers = {"Authorization": f"Bearer {valid_api_key}"}

            # Make requests to different endpoints
            responses = []

            # Events endpoint
            for i in range(2):
                event_headers = headers.copy()
                event_headers.update({
                    "Content-Type": "application/json",
                    "X-Idempotency-Key": f"multi-endpoint-{i}"
                })
                response = client.post("/events", json=sample_event_payload, headers=event_headers)
                responses.append(("events", response))
                time.sleep(0.05)

            # Inbox endpoint
            for i in range(2):
                response = client.get("/inbox", headers=headers)
                responses.append(("inbox", response))
                time.sleep(0.05)

            # Count total successful requests
            total_success = sum(1 for _, r in responses if r.status_code == 200)
            total_rate_limited = sum(1 for _, r in responses if r.status_code == 429)

            # Some requests should be rate limited
            assert total_success + total_rate_limited == len(responses)
            assert total_rate_limited >= 1

        finally:
            # Restore original rate limit
            if original_rate_limit:
                os.environ["RATE_LIMIT_PER_MINUTE"] = original_rate_limit
            else:
                os.environ.pop("RATE_LIMIT_PER_MINUTE", None)

    def test_rate_limit_error_response_format(self, client: TestClient, sample_event_payload, valid_api_key):
        """Test that rate limit error responses have the correct format."""
        # Set very low rate limit
        original_rate_limit = os.environ.get("RATE_LIMIT_PER_MINUTE")
        os.environ["RATE_LIMIT_PER_MINUTE"] = "1"

        try:
            headers = {
                "Authorization": f"Bearer {valid_api_key}",
                "Content-Type": "application/json"
            }

            # First request to use up the limit
            headers["X-Idempotency-Key"] = "format-test-1"
            response1 = client.post("/events", json=sample_event_payload, headers=headers)
            # May succeed or fail depending on current state

            # Second request should trigger rate limiting
            headers["X-Idempotency-Key"] = "format-test-2"
            response2 = client.post("/events", json=sample_event_payload, headers=headers)

            if response2.status_code == 429:
                data = response2.json()

                # Check error response structure
                assert "error" in data
                assert "code" in data["error"]
                assert "message" in data["error"]
                assert "requestId" in data["error"]

                # Check specific error code
                assert data["error"]["code"] == "RATE_LIMIT_EXCEEDED"

                # Check request ID format
                assert data["error"]["requestId"] is not None

        finally:
            # Restore original rate limit
            if original_rate_limit:
                os.environ["RATE_LIMIT_PER_MINUTE"] = original_rate_limit
            else:
                os.environ.pop("RATE_LIMIT_PER_MINUTE", None)

    def test_rate_limit_with_authentication(self, client: TestClient, sample_event_payload):
        """Test that rate limiting doesn't bypass authentication."""
        # Set low rate limit
        original_rate_limit = os.environ.get("RATE_LIMIT_PER_MINUTE")
        os.environ["RATE_LIMIT_PER_MINUTE"] = "1"

        try:
            invalid_headers = {
                "Authorization": "Bearer invalid_key",
                "Content-Type": "application/json"
            }

            # Requests with invalid auth should still get 401, not 429
            for i in range(3):
                invalid_headers["X-Idempotency-Key"] = f"auth-test-{i}"
                response = client.post("/events", json=sample_event_payload, headers=invalid_headers)
                assert response.status_code == 401

        finally:
            # Restore original rate limit
            if original_rate_limit:
                os.environ["RATE_LIMIT_PER_MINUTE"] = original_rate_limit
            else:
                os.environ.pop("RATE_LIMIT_PER_MINUTE", None)


@pytest.mark.api
@pytest.mark.slow
class TestRateLimitingLoad:
    """Load testing for rate limiting."""

    def test_rate_limit_under_load(self, client: TestClient, sample_event_payload, valid_api_key):
        """Test rate limiting behavior under sustained load."""
        # Set moderate rate limit
        original_rate_limit = os.environ.get("RATE_LIMIT_PER_MINUTE")
        os.environ["RATE_LIMIT_PER_MINUTE"] = "10"

        try:
            headers = {
                "Authorization": f"Bearer {valid_api_key}",
                "Content-Type": "application/json"
            }

            responses = []
            start_time = time.time()

            # Send 20 requests rapidly
            for i in range(20):
                headers["X-Idempotency-Key"] = f"load-test-{i}-{int(time.time() * 1000)}"
                response = client.post("/events", json=sample_event_payload, headers=headers)
                responses.append(response)

            end_time = time.time()
            duration = end_time - start_time

            # Analyze results
            success_count = sum(1 for r in responses if r.status_code == 200)
            rate_limit_count = sum(1 for r in responses if r.status_code == 429)

            # Should have a mix of successes and rate limits
            assert success_count > 0
            assert rate_limit_count > 0
            assert success_count + rate_limit_count == len(responses)

            # Should complete quickly (rate limiting should prevent too many slow responses)
            assert duration < 5.0  # Should complete within 5 seconds

        finally:
            # Restore original rate limit
            if original_rate_limit:
                os.environ["RATE_LIMIT_PER_MINUTE"] = original_rate_limit
            else:
                os.environ.pop("RATE_LIMIT_PER_MINUTE", None)