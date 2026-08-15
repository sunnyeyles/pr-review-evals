"""SQLite persistence for tasks and API tokens.

All queries in this module are parameterised. If you need a new filter, add a
bound parameter rather than interpolating into the SQL string.
"""

import hashlib
import sqlite3
import uuid
from typing import Optional

from . import config
from .models import Task, User
from .utils import now_iso

SCHEMA = """
CREATE TABLE IF NOT EXISTS users (
    id        TEXT PRIMARY KEY,
    email     TEXT NOT NULL UNIQUE,
    role      TEXT NOT NULL DEFAULT 'member'
);

CREATE TABLE IF NOT EXISTS api_tokens (
    token_sha TEXT PRIMARY KEY,
    user_id   TEXT NOT NULL REFERENCES users(id),
    revoked   INTEGER NOT NULL DEFAULT 0
);

CREATE TABLE IF NOT EXISTS tasks (
    id         TEXT PRIMARY KEY,
    owner_id   TEXT NOT NULL REFERENCES users(id),
    title      TEXT NOT NULL,
    status     TEXT NOT NULL DEFAULT 'open',
    created_at TEXT NOT NULL,
    due_date   TEXT,
    tags       TEXT NOT NULL DEFAULT ''
);

CREATE INDEX IF NOT EXISTS idx_tasks_owner ON tasks(owner_id, created_at);
"""


def connect(path: Optional[str] = None) -> sqlite3.Connection:
    conn = sqlite3.connect(path or config.DB_PATH)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON")
    return conn


def init_schema(conn: sqlite3.Connection) -> None:
    conn.executescript(SCHEMA)
    conn.commit()


def token_digest(raw_token: str) -> str:
    """Tokens are stored as digests so a database dump does not leak them."""
    return hashlib.sha256(raw_token.encode("utf-8")).hexdigest()


def _row_to_task(row: sqlite3.Row) -> Task:
    return Task(
        id=row["id"],
        owner_id=row["owner_id"],
        title=row["title"],
        status=row["status"],
        created_at=row["created_at"],
        due_date=row["due_date"],
        tags=[t for t in row["tags"].split(",") if t],
    )


def find_user_by_token(conn: sqlite3.Connection, raw_token: str) -> Optional[User]:
    row = conn.execute(
        """
        SELECT users.id, users.email, users.role
          FROM api_tokens
          JOIN users ON users.id = api_tokens.user_id
         WHERE api_tokens.token_sha = ? AND api_tokens.revoked = 0
        """,
        (token_digest(raw_token),),
    ).fetchone()
    if row is None:
        return None
    return User(id=row["id"], email=row["email"], role=row["role"])


def create_user(conn: sqlite3.Connection, email: str, role: str = "member") -> User:
    user = User(id=str(uuid.uuid4()), email=email, role=role)
    conn.execute(
        "INSERT INTO users (id, email, role) VALUES (?, ?, ?)",
        (user.id, user.email, user.role),
    )
    conn.commit()
    return user


def issue_token(conn: sqlite3.Connection, user_id: str, raw_token: str) -> None:
    conn.execute(
        "INSERT INTO api_tokens (token_sha, user_id) VALUES (?, ?)",
        (token_digest(raw_token), user_id),
    )
    conn.commit()


def get_task(conn: sqlite3.Connection, task_id: str) -> Optional[Task]:
    row = conn.execute("SELECT * FROM tasks WHERE id = ?", (task_id,)).fetchone()
    return _row_to_task(row) if row else None


def count_tasks(conn: sqlite3.Connection, owner_id: Optional[str] = None) -> int:
    if owner_id is None:
        row = conn.execute("SELECT COUNT(*) AS n FROM tasks").fetchone()
    else:
        row = conn.execute(
            "SELECT COUNT(*) AS n FROM tasks WHERE owner_id = ?", (owner_id,)
        ).fetchone()
    return int(row["n"])


def list_tasks(
    conn: sqlite3.Connection,
    owner_id: Optional[str],
    limit: int,
    offset: int,
) -> list[Task]:
    if owner_id is None:
        rows = conn.execute(
            "SELECT * FROM tasks ORDER BY created_at DESC LIMIT ? OFFSET ?",
            (limit, offset),
        ).fetchall()
    else:
        rows = conn.execute(
            """
            SELECT * FROM tasks
             WHERE owner_id = ?
             ORDER BY created_at DESC
             LIMIT ? OFFSET ?
            """,
            (owner_id, limit, offset),
        ).fetchall()
    return [_row_to_task(row) for row in rows]


def insert_task(
    conn: sqlite3.Connection,
    owner_id: str,
    title: str,
    due_date: Optional[str] = None,
    tags: Optional[list] = None,
) -> Task:
    task = Task(
        id=str(uuid.uuid4()),
        owner_id=owner_id,
        title=title,
        status="open",
        created_at=now_iso(),
        due_date=due_date,
        tags=list(tags or []),
    )
    conn.execute(
        """
        INSERT INTO tasks (id, owner_id, title, status, created_at, due_date, tags)
        VALUES (?, ?, ?, ?, ?, ?, ?)
        """,
        (
            task.id,
            task.owner_id,
            task.title,
            task.status,
            task.created_at,
            task.due_date,
            ",".join(task.tags),
        ),
    )
    conn.commit()
    return task


def update_task_status(conn: sqlite3.Connection, task_id: str, status: str) -> bool:
    cursor = conn.execute(
        "UPDATE tasks SET status = ? WHERE id = ?", (status, task_id)
    )
    conn.commit()
    return cursor.rowcount > 0
