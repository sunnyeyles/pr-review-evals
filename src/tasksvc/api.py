"""HTTP routing and request handlers.

The module is transport agnostic: :func:`handle` takes a :class:`Request` and
returns ``(status, body_bytes)``. ``server.py`` adapts ``http.server`` onto it,
and the tests call it directly.
"""

import json
import re
import sqlite3
from dataclasses import dataclass, field
from typing import Optional

from . import audit, auth, config, db
from .models import Page, VALID_STATUSES
from .utils import clamp, error, json_body, parse_int

TASK_ID_PATH = re.compile(r"^/tasks/([A-Za-z0-9-]+)$")
TASK_STATUS_PATH = re.compile(r"^/tasks/([A-Za-z0-9-]+)/status$")


@dataclass
class Request:
    method: str
    path: str
    query: dict = field(default_factory=dict)
    headers: dict = field(default_factory=dict)
    body: bytes = b""

    def header(self, name: str) -> Optional[str]:
        for key, value in self.headers.items():
            if key.lower() == name.lower():
                return value
        return None

    def json(self) -> dict:
        if not self.body:
            return {}
        return json.loads(self.body.decode("utf-8"))


def handle(conn: sqlite3.Connection, request: Request) -> tuple[int, bytes]:
    if request.path == "/healthz" and request.method == "GET":
        return 200, json_body({"status": "ok"})

    user = auth.user_from_header(conn, request.header("Authorization"))
    if user is None:
        return error(401, "authentication required")

    if request.path == "/tasks" and request.method == "GET":
        return list_tasks(conn, request, user)
    if request.path == "/tasks" and request.method == "POST":
        return create_task(conn, request, user)
    if request.path == "/tasks/search" and request.method == "GET":
        return search_tasks(conn, request, user)

    match = TASK_STATUS_PATH.match(request.path)
    if match and request.method == "POST":
        return set_status(conn, request, user, match.group(1))

    match = TASK_ID_PATH.match(request.path)
    if match and request.method == "GET":
        return get_task(conn, user, match.group(1))

    return error(404, "no such route")


def list_tasks(conn, request: Request, user) -> tuple[int, bytes]:
    limit = parse_int(request.query.get("limit"), config.DEFAULT_PAGE_SIZE)
    limit = clamp(limit, 1, config.MAX_PAGE_SIZE)
    offset = parse_int(request.query.get("offset"), 0)
    if offset < 0:
        offset = 0

    scope_all = request.query.get("scope") == "all"
    if scope_all and not auth.can_list_all_tasks(user):
        return error(403, "not permitted to list all tasks")

    owner_id = None if scope_all else user.id
    items = db.list_tasks(conn, owner_id, limit, offset)
    total = db.count_tasks(conn, owner_id)
    page = Page(items=items, total=total, limit=limit, offset=offset)
    return 200, json_body(page.to_dict())


def search_tasks(conn, request: Request, user) -> tuple[int, bytes]:
    if not auth.can_list_all_tasks(user):
        return error(403, "not permitted to search tasks")

    term = request.query.get("q", "")
    if not term:
        return error(422, "q is required")

    owner_id = request.query.get("owner_id") or user.id
    limit = parse_int(request.query.get("limit"), config.DEFAULT_PAGE_SIZE)
    items = db.search_tasks(conn, owner_id, term, limit)
    return 200, json_body({"query": term, "items": [t.to_dict() for t in items]})


def create_task(conn, request: Request, user) -> tuple[int, bytes]:
    try:
        payload = request.json()
    except ValueError:
        return error(400, "body must be valid JSON")

    title = (payload.get("title") or "").strip()
    if not title:
        return error(422, "title is required")
    if len(title) > 200:
        return error(422, "title must be 200 characters or fewer")

    tags = payload.get("tags") or []
    if not isinstance(tags, list):
        return error(422, "tags must be a list")

    task = db.insert_task(
        conn,
        owner_id=user.id,
        title=title,
        due_date=payload.get("due_date"),
        tags=[str(tag) for tag in tags],
    )
    audit.record("task.created", actor_id=user.id, subject_id=task.id)
    return 201, json_body(task.to_dict())


def get_task(conn, user, task_id: str) -> tuple[int, bytes]:
    task = db.get_task(conn, task_id)
    if task is None:
        return error(404, "no such task")
    if not auth.can_read_task(user, task):
        return error(403, "not permitted to read this task")
    return 200, json_body(task.to_dict())


def set_status(conn, request: Request, user, task_id: str) -> tuple[int, bytes]:
    try:
        payload = request.json()
    except ValueError:
        return error(400, "body must be valid JSON")

    status = payload.get("status")
    if status not in VALID_STATUSES:
        return error(422, f"status must be one of {', '.join(VALID_STATUSES)}")

    task = db.get_task(conn, task_id)
    if task is None:
        return error(404, "no such task")
    if not auth.can_write_task(user, task):
        return error(403, "not permitted to modify this task")

    db.update_task_status(conn, task_id, status)
    audit.record(
        "task.status_changed",
        actor_id=user.id,
        subject_id=task_id,
        detail={"from": task.status, "to": status},
    )
    task.status = status
    return 200, json_body(task.to_dict())
