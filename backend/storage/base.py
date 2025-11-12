from abc import ABC, abstractmethod
from typing import Optional, List, Dict, Any
from datetime import datetime

from ..models import Event


class StorageInterface(ABC):
    """Abstract interface for event storage implementations."""

    @abstractmethod
    async def initialize(self) -> None:
        """
        Initialize the storage backend (create tables, etc.).
        """
        pass

    @abstractmethod
    async def close(self) -> None:
        """
        Close the storage backend and cleanup resources.
        """
        pass

    @abstractmethod
    async def create_event(
        self,
        tenant_id: Optional[str] = None,
        source: Optional[str] = None,
        event_type: Optional[str] = None,
        topic: Optional[str] = None,
        payload: Optional[Dict[str, Any]] = None,
        idempotency_key: Optional[str] = None,
    ) -> Event:
        """
        Create a new event in storage.

        Args:
            tenant_id: Tenant identifier
            source: Event source (e.g., 'billing')
            event_type: Event type (e.g., 'invoice.paid')
            topic: Event topic (e.g., 'finance')
            payload: Event data payload
            idempotency_key: Optional idempotency key for safe retries

        Returns:
            Event: Created event object

        Raises:
            ValueError: If idempotency key already exists for tenant
        """
        pass

    @abstractmethod
    async def get_event_by_id(self, event_id: str, tenant_id: str) -> Optional[Event]:
        """
        Get event by ID and tenant.

        Args:
            event_id: Event identifier
            tenant_id: Tenant identifier

        Returns:
            Optional[Event]: Event object if found, None otherwise
        """
        pass

    @abstractmethod
    async def get_by_idempotency(
        self, tenant_id: str, idempotency_key: str
    ) -> Optional[Event]:
        """
        Get event by idempotency key and tenant.

        Args:
            tenant_id: Tenant identifier
            idempotency_key: Idempotency key

        Returns:
            Optional[Event]: Event object if found, None otherwise
        """
        pass

    @abstractmethod
    async def get_pending_events(
        self,
        tenant_id: str,
        limit: int = 50,
        since: Optional[datetime] = None,
        topic: Optional[str] = None,
        event_type: Optional[str] = None,
        cursor: Optional[str] = None,
    ) -> tuple[List[Event], Optional[str]]:
        """
        Get pending (undelivered) events for a tenant.

        Args:
            tenant_id: Tenant identifier
            limit: Maximum number of events to return (max 500)
            since: Optional datetime filter (inclusive)
            topic: Optional topic filter
            event_type: Optional event type filter
            cursor: Optional pagination cursor

        Returns:
            tuple[List[Event], Optional[str]]: Events and next cursor
        """
        pass

    @abstractmethod
    async def acknowledge_event(self, event_id: str, tenant_id: str) -> bool:
        """
        Mark event as acknowledged (delivered).

        Args:
            event_id: Event identifier
            tenant_id: Tenant identifier

        Returns:
            bool: True if event was acknowledged, False if not found

        Raises:
            ValueError: If event is not in a state that can be acknowledged
        """
        pass

    @abstractmethod
    async def delete_event(self, event_id: str, tenant_id: str) -> bool:
        """
        Delete an event.

        Args:
            event_id: Event identifier
            tenant_id: Tenant identifier

        Returns:
            bool: True if event was deleted, False if not found

        Raises:
            ValueError: If event is not in a state that can be deleted
        """
        pass

    @abstractmethod
    async def cleanup_old_events(self, ttl_minutes: int = 60) -> int:
        """
        Clean up old acknowledged/deleted events.

        Args:
            ttl_minutes: Time-to-live in minutes for old events

        Returns:
            int: Number of events cleaned up
        """
        pass

    @abstractmethod
    async def health_check(self) -> bool:
        """
        Check if storage backend is healthy.

        Returns:
            bool: True if storage is healthy, False otherwise
        """
        pass
