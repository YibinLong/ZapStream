import time
import asyncio
from typing import Dict
from threading import Lock
from fastapi import HTTPException, Request, status

from .config import get_settings

settings = get_settings()


class TokenBucket:
    """Simple token bucket implementation for rate limiting."""

    def __init__(self, capacity: int, refill_rate: float):
        """
        Initialize token bucket.

        Args:
            capacity: Maximum number of tokens the bucket can hold
            refill_rate: Rate at which tokens are refilled (tokens per second)
        """
        self.capacity = capacity
        self.tokens = capacity
        self.refill_rate = refill_rate
        self.last_refill = time.time()
        self.lock = Lock()

    def consume(self, tokens: int = 1) -> bool:
        """
        Consume tokens from the bucket.

        Args:
            tokens: Number of tokens to consume

        Returns:
            bool: True if tokens were consumed, False if insufficient tokens
        """
        with self.lock:
            # Refill tokens based on elapsed time
            now = time.time()
            elapsed = now - self.last_refill
            tokens_to_add = elapsed * self.refill_rate

            self.tokens = min(self.capacity, self.tokens + tokens_to_add)
            self.last_refill = now

            # Check if we have enough tokens
            if self.tokens >= tokens:
                self.tokens -= tokens
                return True

            return False


class RateLimiter:
    """In-memory rate limiter using token buckets per API key."""

    def __init__(self):
        """Initialize rate limiter with per-client token buckets."""
        self.buckets: Dict[str, TokenBucket] = {}
        self.lock = Lock()

    def get_bucket(self, client_id: str) -> TokenBucket:
        """
        Get or create token bucket for client.

        Args:
            client_id: Client identifier (typically API key or tenant ID)

        Returns:
            TokenBucket: Token bucket for the client
        """
        with self.lock:
            if client_id not in self.buckets:
                # Convert rate limit from per-minute to per-second
                refill_rate = settings.rate_limit_per_minute / 60.0
                self.buckets[client_id] = TokenBucket(
                    capacity=settings.rate_limit_per_minute,
                    refill_rate=refill_rate
                )
            return self.buckets[client_id]

    def is_allowed(self, client_id: str, tokens: int = 1) -> bool:
        """
        Check if request is allowed for client.

        Args:
            client_id: Client identifier
            tokens: Number of tokens required for this request

        Returns:
            bool: True if request is allowed, False otherwise
        """
        bucket = self.get_bucket(client_id)
        return bucket.consume(tokens)

    def get_retry_after(self, client_id: str) -> float:
        """
        Get retry-after seconds for rate limited client.

        Args:
            client_id: Client identifier

        Returns:
            float: Seconds to wait before retry
        """
        bucket = self.get_bucket(client_id)
        # Calculate time needed to refill at least one token
        if bucket.tokens < 1:
            return max(1.0, (1.0 - bucket.tokens) / bucket.refill_rate)
        return 1.0


# Global rate limiter instance
rate_limiter = RateLimiter()


async def check_rate_limit(request: Request):
    """
    Rate limiting middleware function.

    Args:
        request: FastAPI request object

    Raises:
        HTTPException: 429 if rate limit is exceeded
    """
    # Get tenant ID from authenticated request
    tenant_id = getattr(request.state, "tenant_id", None)

    if not tenant_id:
        # If no tenant ID (e.g., for health check), skip rate limiting
        return

    # Check rate limit
    if not rate_limiter.is_allowed(tenant_id):
        retry_after = rate_limiter.get_retry_after(tenant_id)
        raise HTTPException(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            detail="Rate limit exceeded",
            headers={"Retry-After": str(int(retry_after))}
        )