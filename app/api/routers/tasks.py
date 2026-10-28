from http import HTTPStatus
from typing import Annotated

from fastapi import APIRouter, Query

from app.api.dependencies import MAX_ID, TaskId, TaskServiceDep, UserId
from app.api.errors import error_responses
from app.api.schemas import (
    DeleteResult,
    TaskCreate,
    TaskOut,
    TaskPage,
    TaskStatsOut,
    TaskStatusUpdate,
)
from app.domain.enums import TaskStatus

router = APIRouter(tags=["tasks"])

NOT_FOUND_OR_INVALID = error_responses(HTTPStatus.NOT_FOUND, HTTPStatus.UNPROCESSABLE_ENTITY)


@router.post(
    "/users/{user_id}/tasks",
    status_code=HTTPStatus.CREATED,
    responses=NOT_FOUND_OR_INVALID,
)
async def create_task(user_id: UserId, payload: TaskCreate, service: TaskServiceDep) -> TaskOut:
    task = await service.create(user_id, title=payload.title, description=payload.description)
    return TaskOut.model_validate(task)


@router.get("/users/{user_id}/tasks", responses=NOT_FOUND_OR_INVALID)
async def list_tasks(
    user_id: UserId,
    service: TaskServiceDep,
    status: TaskStatus | None = None,
    limit: Annotated[int, Query(ge=1, le=100)] = 20,
    offset: Annotated[int, Query(ge=0, le=MAX_ID)] = 0,
) -> TaskPage:
    page = await service.list_for_user(user_id, status=status, limit=limit, offset=offset)
    return TaskPage.model_validate(page)


@router.get("/users/{user_id}/tasks/stats", responses=NOT_FOUND_OR_INVALID)
async def get_task_stats(user_id: UserId, service: TaskServiceDep) -> TaskStatsOut:
    stats = await service.stats_for_user(user_id)
    return TaskStatsOut.from_stats(stats)


@router.patch("/tasks/{task_id}/status", responses=NOT_FOUND_OR_INVALID)
async def update_task_status(
    task_id: TaskId, payload: TaskStatusUpdate, service: TaskServiceDep
) -> TaskOut:
    task = await service.change_status(task_id, payload.status)
    return TaskOut.model_validate(task)


@router.delete("/tasks/{task_id}", responses=NOT_FOUND_OR_INVALID)
async def delete_task(task_id: TaskId, service: TaskServiceDep) -> DeleteResult:
    await service.delete(task_id)
    return DeleteResult()
