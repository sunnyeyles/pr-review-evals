"""Authentication (who is calling) and authorisation (what they may do)."""

import sqlite3
from typing import Optional

from . import config, db
from .models import Task, User


def user_from_header(conn: sqlite3.Connection, header: Optional[str]) -> Optional[User]:
    """Resolve an ``Authorization: Bearer <token>`` header to a user."""
    if not header:
        return None
    parts = header.split(None, 1)
    if len(parts) != 2 or parts[0].lower() != "bearer":
        return None
    return db.find_user_by_token(conn, parts[1].strip())


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
