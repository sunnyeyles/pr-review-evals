"""Authentication (who is calling) and authorisation (what they may do)."""

import sqlite3
import time
from typing import Optional

from . import config, db
from .models import Task, User

PRINCIPAL_TTL_SECONDS = 900

# Resolved principals keyed by bearer token: token -> (user, resolved_at).
_principals: dict[str, tuple[User, float]] = {}


def reset_cache() -> None:
    """Drop every memoised principal. Used by the tests between cases."""
    _principals.clear()


def _cached_principal(token: str, now: float) -> Optional[User]:
    """Return the memoised principal for *token*, or None once it has aged out."""
    hit = _principals.get(token)
    if hit is None:
        return None
    user, resolved_at = hit
    if now - resolved_at >= PRINCIPAL_TTL_SECONDS:
        del _principals[token]
        return None
    return user


def user_from_header(conn: sqlite3.Connection, header: Optional[str]) -> Optional[User]:
    """Resolve an ``Authorization: Bearer <token>`` header to a user."""
    if not header:
        return None
    parts = header.split(None, 1)
    if len(parts) != 2 or parts[0].lower() != "bearer":
        return None

    token = parts[1].strip()
    now = time.monotonic()
    user = _cached_principal(token, now)
    if user is None:
        user = db.find_user_by_token(conn, token)
        if user is None:
            return None
        _principals[token] = (user, now)
    return user


def can_read_task(user: User, task: Task) -> bool:
    if user.role in config.ADMIN_ROLES:
        return True
    return task.owner_id == user.id


def can_write_task(user: User, task: Task) -> bool:
    """Auditors can read every task but may not change any of them."""
    if user.role == "admin":
        return True
    return task.owner_id == user.id


def can_list_all_tasks(user: User) -> bool:
    return user.role in config.ADMIN_ROLES
