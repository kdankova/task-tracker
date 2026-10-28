from typing import Annotated

from fastapi import Depends, Path, Request

from app.application.ports import UnitOfWork
from app.application.tasks import TaskService
from app.application.users import UserService
from app.infrastructure.db.uow import SqlAlchemyUnitOfWork

MAX_ID = 2**63 - 1  # PostgreSQL BIGINT

UserId = Annotated[int, Path(gt=0, le=MAX_ID)]
TaskId = Annotated[int, Path(gt=0, le=MAX_ID)]


def get_uow(request: Request) -> UnitOfWork:
    return SqlAlchemyUnitOfWork(request.app.state.session_factory)


def get_user_service(uow: Annotated[UnitOfWork, Depends(get_uow)]) -> UserService:
    return UserService(uow)


def get_task_service(uow: Annotated[UnitOfWork, Depends(get_uow)]) -> TaskService:
    return TaskService(uow)


UserServiceDep = Annotated[UserService, Depends(get_user_service)]
TaskServiceDep = Annotated[TaskService, Depends(get_task_service)]
