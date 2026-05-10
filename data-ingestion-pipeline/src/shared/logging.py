import json
import logging
import os
import uuid
from datetime import datetime, timezone
from typing import Any, Dict, Optional


def _utc_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def new_corr_id() -> str:
    return uuid.uuid4().hex


def get_logger(name: str) -> logging.Logger:
    """
    Use standard Python logging. Azure Functions captures stdout/stderr and
    forwards to App Insights when configured.
    """
    logger = logging.getLogger(name)
    level = os.getenv("LOG_LEVEL", "INFO").upper()
    logger.setLevel(level)
    return logger


def log_event(
    logger: logging.Logger,
    message: str,
    *,
    corr_id: Optional[str] = None,
    extra: Optional[Dict[str, Any]] = None,
    level: int = logging.INFO,
) -> None:
    payload: Dict[str, Any] = {
        "ts": _utc_iso(),
        "msg": message,
    }
    if corr_id:
        payload["corr_id"] = corr_id
    if extra:
        payload.update(extra)

    logger.log(level, json.dumps(payload, ensure_ascii=False))


def log_exception(
    logger: logging.Logger,
    message: str,
    *,
    corr_id: Optional[str] = None,
    extra: Optional[Dict[str, Any]] = None,
) -> None:
    """
    Logs the exception stacktrace plus structured context.
    """
    payload: Dict[str, Any] = {
        "ts": _utc_iso(),
        "msg": message,
        "level": "ERROR",
    }
    if corr_id:
        payload["corr_id"] = corr_id
    if extra:
        payload.update(extra)

    # Structured context line
    logger.error(json.dumps(payload, ensure_ascii=False))
    # Stack trace line(s)
    logger.exception(message)


def extract_corr_id(headers: Dict[str, str]) -> Optional[str]:
    """
    Try to pick up a correlation id from incoming request headers.
    """
    for key in ("x-correlation-id", "x-corr-id", "traceparent"):
        if key in headers and headers[key]:
            return headers[key]
    return None
