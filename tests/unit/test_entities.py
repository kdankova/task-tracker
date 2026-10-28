from datetime import timedelta

import pytest

from app.domain.entities import Task, User
from app.domain.enums import TaskStatus


def make_task(status: TaskStatus = TaskStatus.NEW) -> Task:
    task = Task.create(user_id=1, title="Write report")
    task.status = status
    task.created_at = task.updated_at = task.created_at - timedelta(hours=1)
    return task


def test_register_normalises_email_case() -> None:
    user = User.register(email="Ivan@Example.COM", name="Ivan")

    assert user.email == "ivan@example.com"
    assert user.created_at.tzinfo is not None


def test_new_task_starts_as_new_with_equal_timestamps() -> None:
    task = Task.create(user_id=1, title="Write report")

    assert task.status is TaskStatus.NEW
    assert task.description is None
    assert task.created_at == task.updated_at


@pytest.mark.parametrize("current", list(TaskStatus))
@pytest.mark.parametrize("target", list(TaskStatus))
def test_task_can_move_between_any_statuses(current: TaskStatus, target: TaskStatus) -> None:
    task = make_task(current)

    task.change_status(target)

    assert task.status is target


def test_status_change_bumps_updated_at_only() -> None:
    task = make_task()
    created_at, updated_at = task.created_at, task.updated_at

    task.change_status(TaskStatus.IN_PROGRESS)

    assert task.updated_at > updated_at
    assert task.created_at == created_at


@pytest.mark.parametrize("status", list(TaskStatus))
def test_setting_the_same_status_is_a_no_op(status: TaskStatus) -> None:
    task = make_task(status)
    updated_at = task.updated_at

    task.change_status(status)

    assert task.status is status
    assert task.updated_at == updated_at
