from datetime import datetime
from typing import Any, Self

from pydantic import BaseModel, ConfigDict, EmailStr, Field, field_validator

from app.domain.enums import TaskStatus
from app.domain.stats import TaskStats


class InputModel(BaseModel):
    model_config = ConfigDict(extra="forbid", str_strip_whitespace=True)

    @field_validator("*")
    @classmethod
    def reject_nul_characters(cls, value: Any) -> Any:
        # PostgreSQL text cannot store U+0000.
        if isinstance(value, str) and "\x00" in value:
            raise ValueError("must not contain NUL characters")
        return value


class OutputModel(BaseModel):
    model_config = ConfigDict(from_attributes=True)


class UserCreate(InputModel):
    email: EmailStr = Field(examples=["user@example.com"])
    name: str = Field(min_length=1, max_length=255, examples=["Ivan"])


class UserOut(OutputModel):
    id: int
    email: str
    name: str
    created_at: datetime


class TaskCreate(InputModel):
    title: str = Field(min_length=1, max_length=255, examples=["Подготовить отчет"])
    description: str | None = Field(
        default=None, max_length=10_000, examples=["Собрать данные за неделю"]
    )

    @field_validator("description")
    @classmethod
    def blank_description_to_none(cls, value: str | None) -> str | None:
        return value or None


class TaskStatusUpdate(InputModel):
    status: TaskStatus


class TaskOut(OutputModel):
    id: int
    user_id: int
    title: str
    description: str | None
    status: TaskStatus
    created_at: datetime
    updated_at: datetime


class TaskPage(OutputModel):
    items: list[TaskOut]
    total: int
    limit: int
    offset: int


class TaskStatsOut(BaseModel):
    total: int
    new: int
    in_progress: int
    done: int
    cancelled: int

    @classmethod
    def from_stats(cls, stats: TaskStats) -> Self:
        return cls(
            total=stats.total,
            new=stats[TaskStatus.NEW],
            in_progress=stats[TaskStatus.IN_PROGRESS],
            done=stats[TaskStatus.DONE],
            cancelled=stats[TaskStatus.CANCELLED],
        )


class DeleteResult(BaseModel):
    ok: bool = True


class ErrorBody(BaseModel):
    code: str
    message: str
    details: list[dict[str, Any]] | None = None


class ErrorResponse(BaseModel):
    error: ErrorBody
