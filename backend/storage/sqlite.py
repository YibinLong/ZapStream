import os
from typing import Optional, List, Dict, Any, Tuple
from datetime import datetime, timedelta, timezone

from sqlmodel import create_engine, Session, select, and_, or_, func
from sqlmodel.ext.asyncio.session import AsyncSession
from sqlalchemy.ext.asyncio import AsyncEngine
from sqlalchemy.ext.asyncio import create_async_engine
from sqlalchemy.exc import IntegrityError

from ..models import Event, EventStatus
from ..config import get_settings
from .base import StorageInterface

settings = get_settings()


class SQLiteStorage(StorageInterface):
    """SQLite implementation of the storage interface."""

    def __init__(self):
        """Initialize SQLite storage with database connection."""
        # Prefer DATABASE_URL from settings for testability; fallback to local file
        settings = get_settings()
        configured_url = settings.database_url

        if configured_url and configured_url.startswith("sqlite:///"):
            self.database_url = configured_url
        else:
            current_dir = os.path.dirname(os.path.abspath(__file__))
            db_path = os.path.join(current_dir, "data", "events.db")
            # Ensure data directory exists
            db_dir = os.path.dirname(db_path)
            os.makedirs(db_dir, exist_ok=True)
            self.database_url = f"sqlite:///{db_path}"

        # Create async engine
        async_url = self.database_url.replace("sqlite:///", "sqlite+aiosqlite:///")
        self.engine: AsyncEngine = create_async_engine(async_url, echo=settings.debug)

        # Create sync engine for initialization
        self.sync_engine = create_engine(self.database_url, echo=settings.debug)

    async def initialize(self):
        """Initialize database tables."""

        # Create tables using sync engine (simpler for initialization)
        with Session(self.sync_engine) as session:
            # Import SQLModel metadata and create tables
            from sqlmodel import SQLModel

            SQLModel.metadata.create_all(self.sync_engine)

    async def create_event(
        self,
        tenant_id: Optional[str] = None,
        source: Optional[str] = None,
        event_type: Optional[str] = None,
        topic: Optional[str] = None,
        payload: Optional[Dict[str, Any]] = None,
        idempotency_key: Optional[str] = None,
    ) -> Event:
        """Create a new event in SQLite storage."""

        # Support tests passing a pre-constructed Event as the first argument.
        evt_obj: Optional[Event] = None
        if tenant_id is not None and not isinstance(tenant_id, str):
            if isinstance(tenant_id, Event):
                evt_obj = tenant_id
            elif hasattr(tenant_id, "tenant_id"):
                # Some tests construct lightweight objects; treat them like Events.
                evt_obj = tenant_id  # type: ignore[assignment]

        if evt_obj:
            tenant_id = evt_obj.tenant_id
            source = evt_obj.source
            event_type = evt_obj.type
            topic = evt_obj.topic
            payload = evt_obj.payload or {}
            idempotency_key = evt_obj.idempotency_key
        # Basic validation
        if tenant_id is None:
            raise ValueError("tenant_id is required")
        if payload is None:
            payload = {}
        # Check idempotency key if provided
        if idempotency_key:
            existing_event = await self.get_by_idempotency(tenant_id, idempotency_key)
            if existing_event:
                raise ValueError(f"Idempotency key already exists: {idempotency_key}")

        # Preserve provided ID and timestamps if the caller supplied an Event
        if evt_obj:
            event_data: Dict[str, Any] = {
                "tenant_id": tenant_id,
                "source": source,
                "type": event_type,
                "topic": topic,
                "payload": payload,
                "delivered": bool(getattr(evt_obj, "delivered", False)),
                "status": getattr(evt_obj, "status", None) or EventStatus.PENDING,
                "idempotency_key": idempotency_key,
            }
            evt_id = getattr(evt_obj, "id", None)
            if evt_id:
                event_data["id"] = evt_id
            created_at = getattr(evt_obj, "created_at", None)
            if created_at:
                event_data["created_at"] = created_at
            updated_at = getattr(evt_obj, "updated_at", None)
            if updated_at:
                event_data["updated_at"] = updated_at
            event = Event(**event_data)
        else:
            event = Event(
                tenant_id=tenant_id,
                source=source,
                type=event_type,
                topic=topic,
                payload=payload,
                delivered=False,
                status=EventStatus.PENDING,
                idempotency_key=idempotency_key,
            )

        async with AsyncSession(self.engine) as session:
            session.add(event)
            try:
                await session.commit()
            except IntegrityError as exc:
                await session.rollback()
                if idempotency_key:
                    raise ValueError(
                        f"Idempotency key already exists: {idempotency_key}"
                    ) from exc
                raise
            await session.refresh(event)
            return event

    async def get_event_by_id(self, event_id: str, tenant_id: str) -> Optional[Event]:
        """Get event by ID and tenant."""
        async with AsyncSession(self.engine) as session:
            statement = select(Event).where(
                and_(
                    Event.id == event_id,
                    Event.tenant_id == tenant_id,
                    Event.status != EventStatus.DELETED,
                )
            )
            result = await session.exec(statement)
            return result.first()

    async def get_by_idempotency(
        self, tenant_id: str, idempotency_key: str
    ) -> Optional[Event]:
        """Get event by idempotency key and tenant."""
        async with AsyncSession(self.engine) as session:
            statement = select(Event).where(
                and_(
                    Event.tenant_id == tenant_id,
                    Event.idempotency_key == idempotency_key,
                    Event.status != EventStatus.DELETED,
                )
            )
            result = await session.exec(statement)
            return result.first()

    async def get_pending_events(
        self,
        tenant_id: str,
        limit: int = 50,
        since: Optional[datetime] = None,
        topic: Optional[str] = None,
        event_type: Optional[str] = None,
        cursor: Optional[str] = None,
    ) -> Tuple[List[Event], Optional[str]]:
        """Get pending (undelivered) events for a tenant."""

        # Limit validation
        limit = min(max(1, limit), 500)

        # Parse cursor
        cursor_created_at = None
        cursor_id = None
        if cursor:
            try:
                cursor_parts = cursor.split("|")
                if len(cursor_parts) == 2:
                    cursor_created_at = datetime.fromisoformat(cursor_parts[0])
                    cursor_id = cursor_parts[1]
            except (ValueError, IndexError):
                # Invalid cursor, ignore it
                pass

        async with AsyncSession(self.engine) as session:
            # Build base query
            conditions = [
                Event.tenant_id == tenant_id,
                Event.delivered == False,
                Event.status == EventStatus.PENDING,
            ]

            # Add filters
            if since:
                conditions.append(Event.created_at >= since)
            if topic:
                conditions.append(Event.topic == topic)
            if event_type:
                conditions.append(Event.type == event_type)

            # Add cursor filter
            if cursor_created_at and cursor_id:
                conditions.append(
                    or_(
                        Event.created_at > cursor_created_at,
                        and_(
                            Event.created_at == cursor_created_at, Event.id > cursor_id
                        ),
                    )
                )

            statement = (
                select(Event)
                .where(and_(*conditions))
                .order_by(Event.created_at.asc(), Event.id.asc())
                .limit(limit + 1)  # Get one extra to determine if there's a next page
            )

            result = await session.exec(statement)
            events = result.all()

            # Determine if there's a next page and create cursor
            next_cursor = None
            if len(events) > limit:
                events = events[:limit]  # Remove the extra event
                last_event = events[-1]
                next_cursor = f"{last_event.created_at.isoformat()}|{last_event.id}"

            return list(events), next_cursor

    async def acknowledge_event(self, event_id: str, tenant_id: str) -> bool:
        """Mark event as acknowledged (delivered)."""
        async with AsyncSession(self.engine) as session:
            # Get the event first
            statement = select(Event).where(
                and_(
                    Event.id == event_id,
                    Event.tenant_id == tenant_id,
                    Event.status == EventStatus.PENDING,
                )
            )
            result = await session.exec(statement)
            event = result.first()

            if not event:
                return False

            # Update event
            event.delivered = True
            event.status = EventStatus.ACKNOWLEDGED
            event.updated_at = datetime.now(timezone.utc)

            await session.commit()
            return True

    async def delete_event(self, event_id: str, tenant_id: str) -> bool:
        """Delete an event (soft delete by marking as DELETED)."""
        async with AsyncSession(self.engine) as session:
            # Get the event first
            statement = select(Event).where(
                and_(
                    Event.id == event_id,
                    Event.tenant_id == tenant_id,
                    Event.status.in_([EventStatus.PENDING, EventStatus.ACKNOWLEDGED]),
                )
            )
            result = await session.exec(statement)
            event = result.first()

            if not event:
                return False

            # Soft delete
            event.status = EventStatus.DELETED
            event.updated_at = datetime.now(timezone.utc)

            await session.commit()
            return True

    async def cleanup_old_events(self, ttl_minutes: int = 60) -> int:
        """Clean up old acknowledged/deleted events."""
        cutoff_time = datetime.now(timezone.utc) - timedelta(minutes=ttl_minutes)

        async with AsyncSession(self.engine) as session:
            statement = select(Event).where(
                and_(
                    Event.status.in_([EventStatus.ACKNOWLEDGED, EventStatus.DELETED]),
                    Event.updated_at < cutoff_time,
                )
            )
            result = await session.exec(statement)
            events_to_delete = result.all()

            # Hard delete old events
            for event in events_to_delete:
                await session.delete(event)

            await session.commit()
            return len(events_to_delete)

    async def health_check(self) -> bool:
        """Check if SQLite storage is healthy."""
        try:
            async with AsyncSession(self.engine) as session:
                # Simple query to test connection
                await session.exec(select(func.count()).select_from(Event))
                return True
        except Exception:
            return False

    async def close(self) -> None:
        """Close the database engine and cleanup resources."""
        if hasattr(self, "engine") and self.engine:
            await self.engine.dispose()
        if hasattr(self, "sync_engine") and self.sync_engine:
            self.sync_engine.dispose()
