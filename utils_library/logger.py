from __future__ import annotations

import json
import logging
import sys
from datetime import datetime
from typing import Any, Dict, Mapping

try:
    from asgi_correlation_id.context import correlation_id
except Exception:
    correlation_id = None

PII_DENYLIST = {"body", "password", "secret", "token", "note_body"}
MASK = "***"


def _now_iso() -> str:
    return datetime.utcnow().isoformat(timespec="milliseconds") + "Z"


def _mask_pii(d: Mapping[str, Any]) -> Dict[str, Any]:
    out: Dict[str, Any] = {}
    for k, v in d.items():
        if k in PII_DENYLIST and v not in (None, MASK):
            out[k] = MASK
        else:
            out[k] = v
    return out


class JsonFormatter(logging.Formatter):
    def format(self, record: logging.LogRecord) -> str:
        base = {
            "ts": _now_iso(),
            "level": record.levelname,
            "logger": record.name,
            "message": record.getMessage(),
        }
        # добавляем extra-поля
        extra = {
            k: v
            for k, v in record.__dict__.items()
            if k
            not in (
                "args",
                "asctime",
                "created",
                "exc_info",
                "exc_text",
                "filename",
                "funcName",
                "levelname",
                "levelno",
                "lineno",
                "module",
                "msecs",
                "msg",
                "name",
                "pathname",
                "process",
                "processName",
                "relativeCreated",
                "stack_info",
                "thread",
                "threadName",
            )
        }
        # correlation_id
        if "correlation_id" not in extra:
            try:
                if correlation_id is not None:
                    extra["correlation_id"] = correlation_id.get()
            except Exception:
                pass
        # маскируем PII
        extra = _mask_pii(extra)
        base.update(extra)
        return json.dumps(base, ensure_ascii=False)


def setup_logging(level: int = logging.INFO) -> None:
    root = logging.getLogger()
    if root.handlers:
        return
    handler = logging.StreamHandler(sys.stdout)
    handler.setFormatter(JsonFormatter())
    root.addHandler(handler)
    root.setLevel(level)


RESERVED_LOG_RECORD_KEYS = {
    "name",
    "msg",
    "message",
    "args",
    "levelname",
    "levelno",
    "pathname",
    "filename",
    "module",
    "exc_info",
    "exc_text",
    "stack_info",
    "lineno",
    "funcName",
    "created",
    "msecs",
    "relativeCreated",
    "thread",
    "threadName",
    "process",
    "processName",
    "asctime",
}


def _sanitize_extra(payload: dict) -> dict:
    safe = {}
    for k, v in payload.items():
        if k in RESERVED_LOG_RECORD_KEYS:
            safe[f"field_{k}"] = v
        else:
            safe[k] = v
    return safe


class SafeLogger:

    def __init__(self, name: str):
        self._log = logging.getLogger(name)

    def bind(self, **fields: Any) -> "SafeLogger":
        child = SafeLogger(self._log.name)
        child._bound = getattr(self, "_bound", {})
        child._bound = {**child._bound, **fields}
        return child

    def _emit(self, level: int, msg: str, **fields: Any) -> None:
        bound = getattr(self, "_bound", {})
        payload = {**bound, **fields}
        payload = _sanitize_extra(payload)
        self._log.log(level, msg, extra=payload)

    def info(self, msg: str, **fields: Any) -> None:
        self._emit(logging.INFO, msg, **fields)

    def warning(self, msg: str, **fields: Any) -> None:
        self._emit(logging.WARNING, msg, **fields)

    def error(self, msg: str, **fields: Any) -> None:
        self._emit(logging.ERROR, msg, **fields)

    def debug(self, msg: str, **fields: Any) -> None:
        self._emit(logging.DEBUG, msg, **fields)


def get_logger(name: str) -> SafeLogger:
    return SafeLogger(name)
