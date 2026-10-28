from types import TracebackType
from typing import Protocol, Self

from app.application.pagination import Page
from app.domain.entities import Task, User
from app.domain.enums import TaskStatus


class UserRepository(Protocol):
    async def add(self, user: User) -> User:
        """Raises EmailAlreadyTaken if the email is in use."""
        ...

    async def get(self, user_id: int) -> User | None: ...

    async def exists(self, user_id: int) -> bool: ...


class TaskRepository(Protocol):
    async def add(self, task: Task) -> Task: ...

    async def get(self, task_id: int) -> Task | None: ...

    async def save(self, task: Task) -> None: ...

    async def delete(self, task_id: int) -> bool:
        """Returns False if there was no such task."""
        ...

    async def list_for_user(
        self, user_id: int, *, status: TaskStatus | None, limit: int, offset: int
    ) -> Page[Task]:
        """Newest tasks first."""
        ...

    async def count_by_status(self, user_id: int) -> dict[TaskStatus, int]:
        """Statuses without tasks may be absent from the result."""
        ...


class UnitOfWork(Protocol):
    """A single transaction. Changes are discarded unless commit() is called before exit."""

    @property
    def users(self) -> UserRepository: ...

    @property
    def tasks(self) -> TaskRepository: ...

    async def __aenter__(self) -> Self: ...

    async def __aexit__(
        self,
        exc_type: type[BaseException] | None,
        exc: BaseException | None,
        traceback: TracebackType | None,
    ) -> None: ...

    async def commit(self) -> None: ...
