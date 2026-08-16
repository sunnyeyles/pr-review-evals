"""Small helpers shared by the HTTP and storage layers."""

import json
from datetime import datetime, timezone
from typing import Any, Optional


def now_iso() -> str:
    """Current UTC time as an ISO-8601 string, second precision."""
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat()


def json_body(payload: Any) -> bytes:
    return json.dumps(payload, sort_keys=True).encode("utf-8")


def error(status: int, message: str) -> tuple[int, bytes]:
    return status, json_body({"error": message})


def parse_int(raw: Optional[str], default: int) -> int:
    """Parse a query-string integer, falling back to *default* when unusable."""
    if raw is None or raw == "":
        return default
    try:
        return int(raw)
    except (TypeError, ValueError):
        return default


def clamp(value: int, low: int, high: int) -> int:
    return max(low, min(value, high))


def parse_pagination(query: dict, default_limit: int, max_limit: int) -> tuple[int, int]:
    limit = clamp(parse_int(query.get("limit"), default_limit), 1, max_limit)
    offset = max(0, parse_int(query.get("offset"), 0))
    return limit, offset
