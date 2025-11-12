import logging
import sys
from datetime import datetime, timezone
from typing import Any, Dict

from pythonjsonlogger import jsonlogger

from .config import get_settings


class CustomJSONFormatter(jsonlogger.JsonFormatter):
    """Custom JSON formatter with consistent field ordering."""

    def add_fields(
        self,
        log_record: Dict[str, Any],
        record: logging.LogRecord,
        message_dict: Dict[str, Any],
    ):
        """Add custom fields to the log record."""
        super().add_fields(log_record, record, message_dict)

        # Add timestamp
        if not log_record.get("timestamp"):
            log_record["timestamp"] = datetime.now(timezone.utc).isoformat()

        # Add log level
        if log_record.get("level"):
            log_record["level"] = log_record["level"].upper()
        else:
            log_record["level"] = record.levelname

        # Add standard fields
        log_record["logger"] = record.name
        log_record["module"] = record.module
        log_record["function"] = record.funcName
        log_record["line"] = record.lineno

        # Add request context if available (from extra dict)
        if hasattr(record, "request_id"):
            log_record["requestId"] = record.request_id
        if hasattr(record, "tenant_id"):
            log_record["tenantId"] = record.tenant_id
        if hasattr(record, "path"):
            log_record["path"] = record.path
        if hasattr(record, "method"):
            log_record["method"] = record.method
        if hasattr(record, "status_code"):
            log_record["statusCode"] = record.status_code


def setup_logging() -> logging.Logger:
    """Configure structured JSON logging for the application."""
    settings = get_settings()

    # Create logger
    logger = logging.getLogger("zapstream")
    logger.setLevel(getattr(logging, settings.log_level.upper()))

    # Remove any existing handlers
    logger.handlers.clear()

    # Create console handler
    console_handler = logging.StreamHandler(sys.stdout)
    console_handler.setLevel(logging.DEBUG)

    # Create and set formatter
    formatter = CustomJSONFormatter(
        "%(timestamp)s %(level)s %(logger)s %(module)s %(function)s %(line)s %(message)s"
    )
    console_handler.setFormatter(formatter)

    # Add handler to logger
    logger.addHandler(console_handler)

    # Prevent propagation to avoid duplicate logs
    logger.propagate = False

    return logger
