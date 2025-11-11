import os
from typing import List, Optional
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Application settings with environment variable support."""

    # Application settings
    app_env: str = "development"
    port: int = 8000
    log_level: str = "INFO"
    debug: bool = True

    # Environment variable aliases
    backend_port: Optional[int] = None

    @property
    def effective_port(self) -> int:
        """Get the effective port from BACKEND_PORT or port."""
        return self.backend_port or self.port

    # CORS settings
    cors_allowed_origins: str = "http://localhost:3000,http://127.0.0.1:3000"

    @property
    def cors_origins_list(self) -> List[str]:
        """Parse CORS_ALLOWED_ORIGINS string into a list."""
        if self.cors_allowed_origins:
            return [origin.strip() for origin in self.cors_allowed_origins.split(",")]
        return ["http://localhost:3000"]

    # Authentication (MVP: comma-separated key=tenant pairs)
    api_keys: str = "dev_key_123=tenant_dev"

    # Storage settings
    storage_backend: str = "sqlite"  # sqlite | dynamodb
    database_url: str = "sqlite:///./data/events.db"

    # Optional AWS config (only used when STORAGE_BACKEND=dynamodb)
    aws_region: Optional[str] = None
    aws_dynamodb_table: Optional[str] = None

    # Request limits
    max_payload_bytes: int = 524288  # 512KB
    rate_limit_per_minute: int = 60

    # Idempotency window in minutes (clean-up policy)
    idempotency_ttl_min: int = 60

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="allow",
        env_prefix=""
    )

    @property
    def api_key_mapping(self) -> dict[str, str]:
        """Parse API_KEYS environment variable into a dictionary."""
        mapping = {}
        if self.api_keys:
            for pair in self.api_keys.split(","):
                if "=" in pair:
                    key, tenant = pair.strip().split("=", 1)
                    mapping[key] = tenant
        return mapping


# Global settings instance
settings = Settings()


def get_settings() -> Settings:
    """Get the global settings instance."""
    return settings