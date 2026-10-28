from dataclasses import replace

from sqlalchemy import delete, exists, func, insert, select, update
from sqlalchemy.dialects.postgresql import insert as pg_insert
from sqlalchemy.ext.asyncio import AsyncSession

from app.application.pagination import Page
from app.domain.entities import Task, User
from app.domain.enums import TaskStatus
from app.domain.errors import EmailAlreadyTaken
from app.infrastructure.db.models import TaskModel, UserModel


class SqlAlchemyUserRepository:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def add(self, user: User) -> User:
        user_id = await self._session.scalar(
            pg_insert(UserModel)
            .values(email=user.email, name=user.name, created_at=user.created_at)
            .on_conflict_do_nothing(index_elements=[UserModel.email])
            .returning(UserModel.id)
        )
        if user_id is None:
            raise EmailAlreadyTaken
        return replace(user, id=user_id)

    async def get(self, user_id: int) -> User | None:
        model = await self._session.get(UserModel, user_id)
        return _to_user(model) if model else None

    async def exists(self, user_id: int) -> bool:
        return bool(await self._session.scalar(select(exists().where(UserModel.id == user_id))))


class SqlAlchemyTaskRepository:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def add(self, task: Task) -> Task:
        task_id = await self._session.scalar(
            insert(TaskModel)
            .values(
                user_id=task.user_id,
                title=task.title,
                description=task.description,
                status=task.status,
                created_at=task.created_at,
                updated_at=task.updated_at,
            )
            .returning(TaskModel.id)
        )
        return replace(task, id=task_id)

    async def get(self, task_id: int) -> Task | None:
        model = await self._session.get(TaskModel, task_id)
        return _to_task(model) if model else None

    async def save(self, task: Task) -> None:
        await self._session.execute(
            update(TaskModel)
            .where(TaskModel.id == task.id)
            .values(
                title=task.title,
                description=task.description,
                status=task.status,
                updated_at=task.updated_at,
            )
        )

    async def delete(self, task_id: int) -> bool:
        deleted_id = await self._session.scalar(
            delete(TaskModel).where(TaskModel.id == task_id).returning(TaskModel.id)
        )
        return deleted_id is not None

    async def list_for_user(
        self, user_id: int, *, status: TaskStatus | None, limit: int, offset: int
    ) -> Page[Task]:
        filters = [TaskModel.user_id == user_id]
        if status is not None:
            filters.append(TaskModel.status == status)

        total = await self._session.scalar(
            select(func.count()).select_from(TaskModel).where(*filters)
        )
        models = await self._session.scalars(
            select(TaskModel)
            .where(*filters)
            .order_by(TaskModel.created_at.desc(), TaskModel.id.desc())
            .limit(limit)
            .offset(offset)
        )
        return Page(
            items=[_to_task(model) for model in models],
            total=total or 0,
            limit=limit,
            offset=offset,
        )

    async def count_by_status(self, user_id: int) -> dict[TaskStatus, int]:
        rows = await self._session.execute(
            select(TaskModel.status, func.count())
            .where(TaskModel.user_id == user_id)
            .group_by(TaskModel.status)
        )
        return dict(rows.all())


def _to_user(model: UserModel) -> User:
    return User(id=model.id, email=model.email, name=model.name, created_at=model.created_at)


def _to_task(model: TaskModel) -> Task:
    return Task(
        id=model.id,
        user_id=model.user_id,
        title=model.title,
        description=model.description,
        status=model.status,
        created_at=model.created_at,
        updated_at=model.updated_at,
    )
