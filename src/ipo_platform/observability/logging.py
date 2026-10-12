"""
Structured Logging, Correlation Tracking, and Context Propagation for Indian IPO Platform.
Provides JSON formatting, correlation ID / IPO ID context propagation, and secrets redaction.
"""

from contextvars import ContextVar
from datetime import datetime, timezone
import json
import logging
import re
import sys
import traceback
from typing import Any, Dict, Optional, Set

# Context variables for distributed request tracing and domain context
_correlation_id_ctx: ContextVar[Optional[str]] = ContextVar("correlation_id", default=None)
_ipo_id_ctx: ContextVar[Optional[str]] = ContextVar("ipo_id", default=None)

# Standard patterns for sensitive fields to redact
SENSITIVE_KEY_PATTERNS = {
    "password", "secret", "token", "api_key", "apikey", "auth",
    "authorization", "private_key", "access_key", "credential"
}

# Regex to redact passwords in database connection URIs: proto://user:password@host/db
DATABASE_URL_PASSWORD_REGEX = re.compile(r"://([^:]+):([^@]+)@")


def set_correlation_id(correlation_id: Optional[str]) -> None:
    """Sets the current correlation ID in contextvars."""
    _correlation_id_ctx.set(correlation_id)


def get_correlation_id() -> Optional[str]:
    """Retrieves the active correlation ID, if any."""
    return _correlation_id_ctx.get()


def set_ipo_context(ipo_id: Optional[str]) -> None:
    """Sets the active IPO context identifier in contextvars."""
    _ipo_id_ctx.set(ipo_id)


def get_ipo_context() -> Optional[str]:
    """Retrieves the active IPO identifier context, if any."""
    return _ipo_id_ctx.get()


def clear_context() -> None:
    """Clears both correlation and IPO context variables."""
    _correlation_id_ctx.set(None)
    _ipo_id_ctx.set(None)


class LogContextManager:
    """Context manager for setting scoped correlation ID and IPO context."""

    def __init__(self, correlation_id: Optional[str] = None, ipo_id: Optional[str] = None) -> None:
        self.correlation_id = correlation_id
        self.ipo_id = ipo_id
        self.token_corr = None
        self.token_ipo = None

    def __enter__(self) -> "LogContextManager":
        if self.correlation_id is not None:
            self.token_corr = _correlation_id_ctx.set(self.correlation_id)
        if self.ipo_id is not None:
            self.token_ipo = _ipo_id_ctx.set(self.ipo_id)
        return self

    def __exit__(self, exc_type: Any, exc_val: Any, exc_tb: Any) -> None:
        if self.token_corr is not None:
            _correlation_id_ctx.reset(self.token_corr)
        if self.token_ipo is not None:
            _ipo_id_ctx.reset(self.token_ipo)


def redact_secrets(data: Any, sensitive_keys: Optional[Set[str]] = None) -> Any:
    """
    Recursively redacts sensitive keys and values from dictionaries, lists, or strings.
    """
    keys_to_check = sensitive_keys or SENSITIVE_KEY_PATTERNS

    if isinstance(data, dict):
        redacted = {}
        for k, v in data.items():
            k_lower = str(k).lower()
            if any(pattern in k_lower for pattern in keys_to_check):
                redacted[k] = "***REDACTED***"
            else:
                redacted[k] = redact_secrets(v, keys_to_check)
        return redacted
    elif isinstance(data, list):
        return [redact_secrets(item, keys_to_check) for item in data]
    elif isinstance(data, str):
        # Redact database connection passwords
        return DATABASE_URL_PASSWORD_REGEX.sub(r"://\1:***REDACTED***@", data)
    return data


class StructuredJSONFormatter(logging.Formatter):
    """
    Formatter producing single-line JSON log events with context enrichment
    and automated secret redaction.
    """

    def __init__(self, redact: bool = True) -> None:
        super().__init__()
        self.redact = redact

    def format(self, record: logging.LogRecord) -> str:
        # Resolve UTC timestamp
        record_dt = datetime.fromtimestamp(record.created, tz=timezone.utc)
        iso_timestamp = record_dt.isoformat()

        # Build base structured payload
        payload: Dict[str, Any] = {
            "timestamp": iso_timestamp,
            "level": record.levelname,
            "logger": record.name,
            "message": record.getMessage(),
            "correlation_id": getattr(record, "correlation_id", get_correlation_id()),
            "ipo_id": getattr(record, "ipo_id", get_ipo_context()),
        }

        # Include caller code details for warnings, errors, and criticals
        if record.levelno >= logging.WARNING:
            payload["caller"] = {
                "file": record.filename,
                "line": record.lineno,
                "func": record.funcName,
            }

        # Include exception tracebacks
        if record.exc_info:
            payload["exception"] = {
                "type": record.exc_info[0].__name__ if record.exc_info[0] else "Exception",
                "message": str(record.exc_info[1]),
                "stack": traceback.format_exception(*record.exc_info),
            }

        # Include custom extra metadata if present
        extra_fields = {}
        standard_attrs = {
            "name", "msg", "args", "levelname", "levelno", "pathname", "filename",
            "module", "exc_info", "exc_text", "stack_info", "lineno", "funcName",
            "created", "msecs", "relativeCreated", "thread", "threadName",
            "processName", "process", "message", "correlation_id", "ipo_id",
        }
        for attr, value in record.__dict__.items():
            if attr not in standard_attrs and not attr.startswith("_"):
                extra_fields[attr] = value

        if extra_fields:
            payload["extra"] = extra_fields

        if self.redact:
            payload = redact_secrets(payload)

        return json.dumps(payload, default=str)


def setup_logging(
    level: int = logging.INFO,
    json_format: bool = True,
    stream: Optional[Any] = None,
) -> logging.Logger:
    """
    Configures root or application logger with structured JSON formatting.
    """
    root_logger = logging.getLogger()
    root_logger.setLevel(level)

    # Avoid duplicate handlers
    for handler in list(root_logger.handlers):
        root_logger.removeHandler(handler)

    handler = logging.StreamHandler(stream or sys.stdout)
    handler.setLevel(level)

    if json_format:
        handler.setFormatter(StructuredJSONFormatter(redact=True))
    else:
        handler.setFormatter(
            logging.Formatter("[%(asctime)s] [%(levelname)s] [%(name)s]: %(message)s")
        )

    root_logger.addHandler(handler)
    return root_logger


def log_exception(
    logger: logging.Logger,
    exc: Exception,
    message: str = "Unhandled exception encountered",
    level: int = logging.ERROR,
    extra: Optional[Dict[str, Any]] = None,
) -> None:
    """
    Helper function to log an exception with standardized structured metadata.
    """
    extra_payload = extra.copy() if extra else {}
    extra_payload["exception_type"] = exc.__class__.__name__
    extra_payload["exception_message"] = str(exc)
    logger.log(level, message, exc_info=exc, extra=extra_payload)
