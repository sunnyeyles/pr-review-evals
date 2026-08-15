"""Domain objects exchanged between the storage layer and the HTTP layer."""

from dataclasses import dataclass, field
from typing import Any, Optional

VALID_STATUSES = ("open", "in_progress", "done", "cancelled")

@dataclass(frozen=True)
class User:
    id: str
    email: str
    role: str


    @property
    def is_admin(self) -> bool:
        return self.role == "admin"


@dataclass
class Task:
    id: str
    owner_id: str
    title: str
    status: str
    created_at: str   
    due_date: Optional[str] = None
    tags: list = field(default_factory=list)

    def to_dict(self) -> dict:
        return {
            "id": self.id,
            "owner_id": self.owner_id,
            "title": self.title,
            "status": self.status,
            "created_at": self.created_at,
            "due_date": self.due_date,
            "tags": list(self.tags),
        }


@dataclass
class Page:
    """One slice of a listing, plus the cursor the client needs to continue."""

    items: list
    total: int
    limit: int
    offset: int

    @property
    def next_offset(self) -> Optional[int]:
        consumed = self.offset + len(self.items)
        return consumed if consumed < self.total else None

    def to_dict(self) -> dict[str, Any]:
        return {
            "items": [item.to_dict() for item in self.items],
            "total": self.total,
            "limit": self.limit,
            "offset": self.offset,
            "next_offset": self.next_offset,
        }
