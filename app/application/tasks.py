from app.application.pagination import Page
from app.application.ports import UnitOfWork
from app.domain.entities import Task
from app.domain.enums import TaskStatus
from app.domain.errors import TaskNotFound, UserNotFound
from app.domain.stats import TaskStats


class TaskService:
    def __init__(self, uow: UnitOfWork) -> None:
        self._uow = uow

    async def create(self, user_id: int, *, title: str, description: str | None) -> Task:
        async with self._uow as uow:
            await _ensure_user_exists(uow, user_id)
            task = await uow.tasks.add(
                Task.create(user_id=user_id, title=title, description=description)
            )
            await uow.commit()
        return task

    async def list_for_user(
        self, user_id: int, *, status: TaskStatus | None, limit: int, offset: int
    ) -> Page[Task]:
        async with self._uow as uow:
            await _ensure_user_exists(uow, user_id)
            return await uow.tasks.list_for_user(user_id, status=status, limit=limit, offset=offset)

    async def change_status(self, task_id: int, status: TaskStatus) -> Task:
        async with self._uow as uow:
            task = await uow.tasks.get(task_id)
            if task is None:
                raise TaskNotFound(task_id)
            task.change_status(status)
            await uow.tasks.save(task)
            await uow.commit()
        return task

    async def delete(self, task_id: int) -> None:
        async with self._uow as uow:
            if not await uow.tasks.delete(task_id):
                raise TaskNotFound(task_id)
            await uow.commit()

    async def stats_for_user(self, user_id: int) -> TaskStats:
        async with self._uow as uow:
            await _ensure_user_exists(uow, user_id)
            counts = await uow.tasks.count_by_status(user_id)
        return TaskStats.from_counts(counts)


async def _ensure_user_exists(uow: UnitOfWork, user_id: int) -> None:
    if not await uow.users.exists(user_id):
        raise UserNotFound(user_id)
