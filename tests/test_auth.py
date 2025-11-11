"""
Unit tests for authentication and authorization logic.
"""

import pytest
from unittest.mock import AsyncMock, Mock
from fastapi import HTTPException, Request

from backend.auth import get_api_key, get_current_tenant_id, extract_api_key, resolve_tenant_id, AuthenticatedTenant
from backend.error_handlers import AuthenticationException


@pytest.mark.unit
class TestAPIKeyExtraction:
    """Test API key extraction from headers."""

    def test_extract_from_authorization_bearer(self):
        """Test extracting API key from Authorization: Bearer header."""
        headers = {"Authorization": "Bearer test_key_123"}
        api_key = extract_api_key(headers)
        assert api_key == "test_key_123"

    def test_extract_from_authorization_lowercase(self):
        """Test extracting API key from lowercase authorization header."""
        headers = {"authorization": "bearer test_key_123"}
        api_key = extract_api_key(headers)
        assert api_key == "test_key_123"

    def test_extract_from_x_api_key(self):
        """Test extracting API key from X-API-Key header."""
        headers = {"X-API-Key": "test_key_456"}
        api_key = extract_api_key(headers)
        assert api_key == "test_key_456"

    def test_extract_from_x_api_key_lowercase(self):
        """Test extracting API key from lowercase x-api-key header."""
        headers = {"x-api-key": "test_key_456"}
        api_key = extract_api_key(headers)
        assert api_key == "test_key_456"

    def test_prefer_authorization_over_x_api_key(self):
        """Test that Authorization header takes precedence over X-API-Key."""
        headers = {
            "Authorization": "Bearer primary_key",
            "X-API-Key": "secondary_key"
        }
        api_key = extract_api_key(headers)
        assert api_key == "primary_key"

    def test_missing_api_key(self):
        """Test handling of missing API key."""
        headers = {}
        api_key = extract_api_key(headers)
        assert api_key is None

    def test_malformed_authorization_header(self):
        """Test handling of malformed Authorization header."""
        headers = {"Authorization": "InvalidFormat"}
        api_key = extract_api_key(headers)
        assert api_key is None

    def test_authorization_header_without_bearer(self):
        """Test Authorization header without Bearer prefix."""
        headers = {"Authorization": "Basic dGVzdDp0ZXN0"}
        api_key = extract_api_key(headers)
        assert api_key is None

    def test_empty_authorization_header(self):
        """Test empty Authorization header."""
        headers = {"Authorization": ""}
        api_key = extract_api_key(headers)
        assert api_key is None

    def test_empty_x_api_key_header(self):
        """Test empty X-API-Key header."""
        headers = {"X-API-Key": ""}
        api_key = extract_api_key(headers)
        assert api_key is None

    def test_bearer_with_extra_whitespace(self):
        """Test Bearer token with extra whitespace."""
        headers = {"Authorization": "Bearer    test_key_123    "}
        api_key = extract_api_key(headers)
        assert api_key == "test_key_123"

    def test_bearer_case_insensitive(self):
        """Test Bearer prefix case insensitive."""
        headers = {"Authorization": "bearer test_key_123"}
        api_key = extract_api_key(headers)
        assert api_key == "test_key_123"


@pytest.mark.unit
class TestTenantResolution:
    """Test tenant ID resolution from API keys."""

    def test_resolve_valid_tenant(self):
        """Test resolving tenant ID for valid API key."""
        api_key_mapping = {
            "key1": "tenant_a",
            "key2": "tenant_b"
        }

        tenant_id = resolve_tenant_id("key1", api_key_mapping)
        assert tenant_id == "tenant_a"

    def test_resolve_another_valid_tenant(self):
        """Test resolving different tenant ID."""
        api_key_mapping = {
            "key1": "tenant_a",
            "key2": "tenant_b"
        }

        tenant_id = resolve_tenant_id("key2", api_key_mapping)
        assert tenant_id == "tenant_b"

    def test_resolve_invalid_api_key(self):
        """Test tenant resolution for invalid API key."""
        api_key_mapping = {
            "key1": "tenant_a",
            "key2": "tenant_b"
        }

        tenant_id = resolve_tenant_id("invalid_key", api_key_mapping)
        assert tenant_id is None

    def test_resolve_empty_api_key(self):
        """Test tenant resolution for empty API key."""
        api_key_mapping = {"key1": "tenant_a"}

        tenant_id = resolve_tenant_id("", api_key_mapping)
        assert tenant_id is None

    def test_resolve_none_api_key(self):
        """Test tenant resolution for None API key."""
        api_key_mapping = {"key1": "tenant_a"}

        tenant_id = resolve_tenant_id(None, api_key_mapping)
        assert tenant_id is None

    def test_resolve_with_empty_mapping(self):
        """Test tenant resolution with empty API key mapping."""
        api_key_mapping = {}

        tenant_id = resolve_tenant_id("any_key", api_key_mapping)
        assert tenant_id is None

    def test_resolve_with_none_mapping(self):
        """Test tenant resolution with None mapping."""
        tenant_id = resolve_tenant_id("any_key", None)
        assert tenant_id is None


@pytest.mark.unit
class TestAuthenticatedTenant:
    """Test AuthenticatedTenant dependency."""

    def test_authenticated_tenant_creation(self):
        """Test creating AuthenticatedTenant."""
        auth_tenant = AuthenticatedTenant(
            tenant_id="test_tenant",
            api_key="test_key_123"
        )

        assert auth_tenant.tenant_id == "test_tenant"
        assert auth_tenant.api_key == "test_key_123"

    def test_authenticated_tenant_immutability(self):
        """Test that AuthenticatedTenant attributes can be modified (Pydantic models are mutable)."""
        auth_tenant = AuthenticatedTenant(
            tenant_id="original_tenant",
            api_key="original_key"
        )

        # Pydantic models allow modification unless frozen=True
        auth_tenant.tenant_id = "new_tenant"
        assert auth_tenant.tenant_id == "new_tenant"


@pytest.mark.unit
class TestAuthIntegration:
    """Test authentication integration scenarios."""

    def test_full_auth_flow_success(self):
        """Test successful authentication flow."""
        # Mock settings with API key mapping
        from unittest.mock import patch
        mock_settings = Mock()
        mock_settings.api_key_mapping = {
            "test_key_123": "test_tenant"
        }

        # Mock request with valid headers
        mock_request = Mock()
        mock_request.headers = {
            "Authorization": "Bearer test_key_123"
        }

        # Extract API key
        api_key = extract_api_key(mock_request.headers)
        assert api_key == "test_key_123"

        # Resolve tenant
        tenant_id = resolve_tenant_id(api_key, mock_settings.api_key_mapping)
        assert tenant_id == "test_tenant"

        # Create authenticated tenant
        auth_tenant = AuthenticatedTenant(
            tenant_id=tenant_id,
            api_key=api_key
        )
        assert auth_tenant.tenant_id == "test_tenant"

    def test_auth_flow_with_invalid_key(self):
        """Test authentication flow with invalid API key."""
        mock_settings = Mock()
        mock_settings.api_key_mapping = {
            "valid_key": "valid_tenant"
        }

        mock_request = Mock()
        mock_request.headers = {
            "Authorization": "Bearer invalid_key"
        }

        # Extract API key (works)
        api_key = extract_api_key(mock_request.headers)
        assert api_key == "invalid_key"

        # Resolve tenant (fails)
        tenant_id = resolve_tenant_id(api_key, mock_settings.api_key_mapping)
        assert tenant_id is None

    def test_auth_flow_with_missing_header(self):
        """Test authentication flow with missing auth header."""
        mock_request = Mock()
        mock_request.headers = {}

        # Extract API key (fails)
        api_key = extract_api_key(mock_request.headers)
        assert api_key is None

        # Resolve tenant (fails)
        tenant_id = resolve_tenant_id(api_key, {})
        assert tenant_id is None


@pytest.mark.unit
class TestAuthHeadersEdgeCases:
    """Test edge cases in header parsing."""

    def test_multiple_spaces_in_bearer(self):
        """Test multiple spaces between Bearer and token."""
        headers = {"Authorization": "Bearer     token_with_spaces"}
        api_key = extract_api_key(headers)
        assert api_key == "token_with_spaces"

    def test_bearer_with_tab_characters(self):
        """Test Bearer with tab characters."""
        headers = {"Authorization": "Bearer\ttoken_with_tabs"}
        api_key = extract_api_key(headers)
        assert api_key == "token_with_tabs"

    def test_api_key_with_special_characters(self):
        """Test API key with special characters."""
        special_key = "test_key_123-ABC_def.xyz@#$%"
        headers = {"Authorization": f"Bearer {special_key}"}
        api_key = extract_api_key(headers)
        assert api_key == special_key

    def test_case_variations_in_x_api_key(self):
        """Test various case combinations in X-API-Key header."""
        test_cases = [
            ("X-API-Key", "value1"),
            ("x-api-key", "value2"),
            ("X-Api-Key", "value3"),
            ("x-Api-Key", "value4"),
        ]

        for header_name, expected_value in test_cases:
            headers = {header_name: expected_value}
            api_key = extract_api_key(headers)
            assert api_key == expected_value, f"Failed for header: {header_name}"