from collections import Counter
from collections.abc import Iterator
from dataclasses import replace
from itertools import count
from types import TracebackType
from typing import Self

from app.application.pagination import Page
from app.domain.entities import Task, User
from app.domain.enums import TaskStatus
from app.domain.errors import EmailAlreadyTaken


class FakeUserRepository:
    def __init__(self, rows: dict[int, User], ids: Iterator[int]) -> None:
        self.rows = rows
        self._ids = ids

    async def add(self, user: User) -> User:
        if any(existing.email == user.email for existing in self.rows.values()):
            raise EmailAlreadyTaken
        user_id = next(self._ids)
        self.rows[user_id] = replace(user, id=user_id)
        return replace(user, id=user_id)

    async def get(self, user_id: int) -> User | None:
        user = self.rows.get(user_id)
        return replace(user) if user else None

    async def exists(self, user_id: int) -> bool:
        return user_id in self.rows


class FakeTaskRepository:
    def __init__(self, rows: dict[int, Task], ids: Iterator[int]) -> None:
        self.rows = rows
        self._ids = ids

    async def add(self, task: Task) -> Task:
        task_id = next(self._ids)
        self.rows[task_id] = replace(task, id=task_id)
        return replace(task, id=task_id)

    async def get(self, task_id: int) -> Task | None:
        task = self.rows.get(task_id)
        return replace(task) if task else None

    async def save(self, task: Task) -> None:
        assert task.id is not None
        self.rows[task.id] = replace(task)

    async def delete(self, task_id: int) -> bool:
        return self.rows.pop(task_id, None) is not None

    async def list_for_user(
        self, user_id: int, *, status: TaskStatus | None, limit: int, offset: int
    ) -> Page[Task]:
        matching = sorted(
            (
                task
                for task in self.rows.values()
                if task.user_id == user_id and status in (None, task.status)
            ),
            key=lambda task: (task.created_at, task.id),
            reverse=True,
        )
        return Page(
            items=matching[offset : offset + limit], total=len(matching), limit=limit, offset=offset
        )

    async def count_by_status(self, user_id: int) -> dict[TaskStatus, int]:
        return dict(Counter(task.status for task in self.rows.values() if task.user_id == user_id))


class FakeUnitOfWork:
    users: FakeUserRepository
    tasks: FakeTaskRepository

    def __init__(self) -> None:
        self.committed_users: dict[int, User] = {}
        self.committed_tasks: dict[int, Task] = {}
        self.commits = 0
        self._user_ids = count(1)
        self._task_ids = count(1)

    async def __aenter__(self) -> Self:
        self.users = FakeUserRepository(dict(self.committed_users), self._user_ids)
        self.tasks = FakeTaskRepository(dict(self.committed_tasks), self._task_ids)
        return self

    async def __aexit__(
        self,
        exc_type: type[BaseException] | None,
        exc: BaseException | None,
        traceback: TracebackType | None,
    ) -> None:
        return None

    async def commit(self) -> None:
        self.committed_users = dict(self.users.rows)
        self.committed_tasks = dict(self.tasks.rows)
        self.commits += 1
