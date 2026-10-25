"""Structured JSON logging with request context and secret redaction."""

import json
import logging
import sys
import time
from collections.abc import Iterator
from contextlib import contextmanager
from contextvars import ContextVar
from datetime import UTC, datetime
from typing import Any

request_id_var: ContextVar[str | None] = ContextVar("request_id", default=None)
user_id_var: ContextVar[str | None] = ContextVar("user_id", default=None)

_SENSITIVE_MARKERS = (
    "password",
    "secret",
    "token",
    "authorization",
    "api_key",
    "apikey",
    "signature",
    "cookie",
)
_RESERVED_ATTRS = set(vars(logging.LogRecord("", 0, "", 0, "", (), None))) | {
    "message",
    "asctime",
    "taskName",
    "color_message",
}


def redact(value: Any, key: str = "") -> Any:
    """Replace values whose key looks sensitive; recurse into dicts and lists."""
    if key and any(marker in key.lower() for marker in _SENSITIVE_MARKERS):
        return "[REDACTED]"
    if isinstance(value, dict):
        return {k: redact(v, str(k)) for k, v in value.items()}
    if isinstance(value, list | tuple):
        return [redact(v) for v in value]
    return value


class JsonFormatter(logging.Formatter):
    def format(self, record: logging.LogRecord) -> str:
        payload: dict[str, Any] = {
            "timestamp": datetime.fromtimestamp(record.created, UTC).isoformat(),
            "level": record.levelname,
            "logger": record.name,
            "message": record.getMessage(),
            "request_id": request_id_var.get(),
            "user_id": user_id_var.get(),
        }
        for key, value in vars(record).items():
            if key not in _RESERVED_ATTRS and not key.startswith("_"):
                payload[key] = redact(value, key)
        if record.exc_info and record.exc_info[0] is not None:
            payload["exception"] = {
                "type": record.exc_info[0].__name__,
                "traceback": self.formatException(record.exc_info),
            }
        return json.dumps(payload, default=str, ensure_ascii=False)


def configure_logging(level: str = "INFO") -> None:
    handler = logging.StreamHandler(sys.stdout)
    handler.setFormatter(JsonFormatter())
    handler.set_name("brightway-json")
    root = logging.getLogger()
    # Replace only our own handler, so repeated app creation does not duplicate output
    # and handlers installed by others (e.g. pytest's log capture) keep working.
    root.handlers[:] = [h for h in root.handlers if h.get_name() != "brightway-json"]
    root.addHandler(handler)
    root.setLevel(level.upper())
    for name in ("uvicorn", "uvicorn.error"):
        uvicorn_logger = logging.getLogger(name)
        uvicorn_logger.handlers.clear()
        uvicorn_logger.propagate = True
    # The request middleware writes one structured line per request instead.
    logging.getLogger("uvicorn.access").disabled = True
    logging.getLogger("httpx").setLevel(logging.WARNING)
    logging.getLogger("httpcore").setLevel(logging.WARNING)


def _elapsed_ms(started: float) -> float:
    return round((time.perf_counter() - started) * 1000, 2)


@contextmanager
def log_operation(logger: logging.Logger, operation: str, **fields: Any) -> Iterator[None]:
    """Log the outcome and duration of an important operation."""
    started = time.perf_counter()
    try:
        yield
    except Exception as exc:
        logger.warning(
            "operation failed",
            extra={
                "operation": operation,
                "status": "failed",
                "duration_ms": _elapsed_ms(started),
                "error": {"type": type(exc).__name__, "detail": str(exc)},
                **fields,
            },
        )
        raise
    logger.info(
        "operation completed",
        extra={
            "operation": operation,
            "status": "success",
            "duration_ms": _elapsed_ms(started),
            **fields,
        },
    )
