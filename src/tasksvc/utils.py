"""Small helpers shared by the HTTP and storage layers."""

import json
from datetime import datetime, timezone
from typing import Any, Iterable, Optional


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


def first_present(input: dict, *names: str) -> Any:
    """Return the value of the first name present in *input*, else None."""
    for name in names:
        if name in input:
            return input[name]
    return None
