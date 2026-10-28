from dataclasses import dataclass
from datetime import UTC, datetime
from typing import Self

from app.domain.enums import TaskStatus


def utc_now() -> datetime:
    return datetime.now(UTC)


@dataclass(kw_only=True)
class User:
    email: str
    name: str
    created_at: datetime
    id: int | None = None

    @classmethod
    def register(cls, *, email: str, name: str) -> Self:
        return cls(email=email.lower(), name=name, created_at=utc_now())


@dataclass(kw_only=True)
class Task:
    user_id: int
    title: str
    description: str | None
    status: TaskStatus
    created_at: datetime
    updated_at: datetime
    id: int | None = None

    @classmethod
    def create(cls, *, user_id: int, title: str, description: str | None = None) -> Self:
        now = utc_now()
        return cls(
            user_id=user_id,
            title=title,
            description=description,
            status=TaskStatus.NEW,
            created_at=now,
            updated_at=now,
        )

    def change_status(self, status: TaskStatus) -> None:
        if status == self.status:
            return
        self.status = status
        self.updated_at = utc_now()
