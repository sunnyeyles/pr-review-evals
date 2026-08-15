"""Append-only audit trail.

Every state change that a privileged caller makes has to land here. The file is
consumed by the compliance exporter, so entries must never be dropped silently.
"""

import json
import os
from typing import Optional

from . import config
from .utils import now_iso


def _line(action: str, actor_id: str, subject_id: Optional[str], detail: dict) -> str:
    record = {
        "at": now_iso(),
        "action": action,
        "actor_id": actor_id,
        "subject_id": subject_id,
        "detail": detail,
    }
    return json.dumps(record, sort_keys=True)


def record(
    action: str,
    actor_id: str,
    subject_id: Optional[str] = None,
    detail: Optional[dict] = None,
) -> None:
    """Append one audit entry.

    Raises ``OSError`` if the entry cannot be written. Callers must not swallow
    that error: an unrecorded privileged action is a compliance failure.
    """
    path = config.AUDIT_LOG_PATH
    directory = os.path.dirname(path)
    if directory:
        os.makedirs(directory, exist_ok=True)
    with open(path, "a", encoding="utf-8") as handle:
        handle.write(_line(action, actor_id, subject_id, detail or {}) + "\n")


def read_all() -> list:
    """Return every audit entry, oldest first. Used by the exporter and tests."""
    if not os.path.exists(config.AUDIT_LOG_PATH):
        return []
    with open(config.AUDIT_LOG_PATH, encoding="utf-8") as handle:
        return [json.loads(line) for line in handle if line.strip()]
