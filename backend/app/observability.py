"""Request diagnostics without request bodies, query strings or provider secrets."""
from __future__ import annotations

import json
import logging
import os
import re
import time
import traceback
from contextvars import ContextVar
from uuid import uuid4

from fastapi import Request
from fastapi.responses import JSONResponse

request_id = ContextVar("request_id", default=None)


class JsonFormatter(logging.Formatter):
    def format(self, record: logging.LogRecord) -> str:
        return json.dumps({"timestamp": self.formatTime(record), "level": record.levelname,
                           "logger": record.name, "request_id": request_id.get(),
                           "message": record.getMessage(), **getattr(record, "fields", {})})


def configure_logging() -> None:
    logger = logging.getLogger("carecompass")
    if not any(getattr(handler, "carecompass", False) for handler in logger.handlers):
        handler = logging.StreamHandler()
        handler.carecompass = True
        handler.setFormatter(JsonFormatter())
        logger.addHandler(handler)
    level = os.getenv("LOG_LEVEL", "INFO").upper()
    logger.setLevel(level if level in {"DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"} else "INFO")
    logger.propagate = False


async def log_request(request: Request, call_next):
    incoming = request.headers.get("x-request-id", "")
    identifier = incoming if re.fullmatch(r"[A-Za-z0-9_-]{1,64}", incoming) else uuid4().hex
    token = request_id.set(identifier)
    started = time.perf_counter()
    logger = logging.getLogger("carecompass.http")
    fields = {"event": "http_request", "method": request.method, "path": request.url.path}
    try:
        try:
            response = await call_next(request)
        except Exception as error:
            # Stack locations suffice to find the failing line; exception text may contain patient data.
            fields.update(error_type=type(error).__name__, stack=[
                f"{frame.filename}:{frame.lineno}:{frame.name}" for frame in traceback.extract_tb(error.__traceback__)
            ])
            response = JSONResponse({"error": "INTERNAL_SERVER_ERROR"}, status_code=500)
        fields.update(status=response.status_code, duration_ms=round((time.perf_counter() - started) * 1000))
        level = logging.ERROR if response.status_code >= 500 else logging.WARNING if response.status_code >= 400 else logging.INFO
        logger.log(level, "request completed", extra={"fields": fields})
        response.headers["X-Request-ID"] = identifier
        return response
    finally:
        request_id.reset(token)
