import json
import logging
import sys
from datetime import datetime, timezone
from contextvars import ContextVar
from typing import Any, Optional

request_id_var: ContextVar[Optional[str]] = ContextVar(
    "request_id",
    default=None,
)


class JsonFormatter(logging.Formatter):
    def format(
        self,
        record: logging.LogRecord,
    ) -> str:  # type: ignore[override]
        msg = record.getMessage()
        payload: dict[str, Any] = {
            "ts": datetime.now(timezone.utc).isoformat(),
            "level": record.levelname,
            "logger": record.name,
            "msg": msg,
        }

        rid = getattr(record, "request_id", None) or request_id_var.get()
        if rid:
            payload["request_id"] = rid

        for k, v in record.__dict__.items():
            if k in (
                "name",
                "msg",
                "args",
                "levelname",
                "levelno",
                "request_id",
            ):
                continue
            if k.startswith("_"):
                continue
            try:
                json.dumps({k: v})
                payload[k] = v
            except Exception:
                payload[k] = str(v)

        return json.dumps(payload, default=str)


class ContextFilter(logging.Filter):
    def filter(
        self,
        record: logging.LogRecord,
    ) -> bool:  # type: ignore[override]
        try:
            rid = request_id_var.get()
        except Exception:
            rid = None
        if rid:
            record.request_id = rid
        return True


def bind_request_id(rid: str):
    return request_id_var.set(rid)


def reset_request_id(token):
    try:
        request_id_var.reset(token)
    except Exception:
        pass


def configure_logging() -> None:
    root = logging.getLogger()
    if root.handlers:
        return

    handler = logging.StreamHandler(sys.stdout)
    handler.setFormatter(JsonFormatter())
    root.setLevel(logging.INFO)
    root.addHandler(handler)
    root.addFilter(ContextFilter())


__all__ = [
    "configure_logging",
    "bind_request_id",
    "reset_request_id",
    "request_id_var",
]
