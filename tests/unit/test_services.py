import pytest

from app.application.tasks import TaskService
from app.application.users import UserService
from app.domain.enums import TaskStatus
from app.domain.errors import (
    EmailAlreadyTaken,
    TaskNotFound,
    UserNotFound,
)
from tests.unit.fakes import FakeUnitOfWork


@pytest.fixture
def uow() -> FakeUnitOfWork:
    return FakeUnitOfWork()


@pytest.fixture
def users(uow: FakeUnitOfWork) -> UserService:
    return UserService(uow)


@pytest.fixture
def tasks(uow: FakeUnitOfWork) -> TaskService:
    return TaskService(uow)


@pytest.fixture
async def user_id(users: UserService) -> int:
    user = await users.register(email="ivan@example.com", name="Ivan")
    assert user.id is not None
    return user.id


class TestUserService:
    async def test_register_persists_and_commits(
        self, users: UserService, uow: FakeUnitOfWork
    ) -> None:
        user = await users.register(email="Ivan@Example.com", name="Ivan")

        assert user.id is not None
        assert await users.get(user.id) == user
        assert user.email == "ivan@example.com"
        assert uow.commits == 1

    async def test_email_uniqueness_ignores_case(
        self, users: UserService, uow: FakeUnitOfWork, user_id: int
    ) -> None:
        with pytest.raises(EmailAlreadyTaken):
            await users.register(email="IVAN@example.com", name="Other Ivan")

        assert uow.commits == 1

    async def test_get_unknown_user(self, users: UserService) -> None:
        with pytest.raises(UserNotFound):
            await users.get(404)


class TestTaskService:
    async def test_create_task_for_unknown_user_is_rejected(
        self, tasks: TaskService, uow: FakeUnitOfWork
    ) -> None:
        with pytest.raises(UserNotFound):
            await tasks.create(404, title="Orphan", description=None)

        assert uow.committed_tasks == {}
        assert uow.commits == 0

    async def test_change_status_persists_the_new_status(
        self, tasks: TaskService, uow: FakeUnitOfWork, user_id: int
    ) -> None:
        task = await tasks.create(user_id, title="Report", description=None)
        assert task.id is not None

        updated = await tasks.change_status(task.id, TaskStatus.DONE)

        assert updated.status is TaskStatus.DONE
        assert uow.committed_tasks[task.id].status is TaskStatus.DONE

    async def test_delete_removes_the_task(
        self, tasks: TaskService, uow: FakeUnitOfWork, user_id: int
    ) -> None:
        task = await tasks.create(user_id, title="Report", description=None)
        assert task.id is not None

        await tasks.delete(task.id)

        assert task.id not in uow.committed_tasks

    async def test_change_status_of_unknown_task(self, tasks: TaskService) -> None:
        with pytest.raises(TaskNotFound):
            await tasks.change_status(404, TaskStatus.DONE)

    async def test_delete_unknown_task(self, tasks: TaskService, uow: FakeUnitOfWork) -> None:
        with pytest.raises(TaskNotFound):
            await tasks.delete(404)

        assert uow.commits == 0

    async def test_listing_and_stats_require_an_existing_user(self, tasks: TaskService) -> None:
        with pytest.raises(UserNotFound):
            await tasks.list_for_user(404, status=None, limit=10, offset=0)
        with pytest.raises(UserNotFound):
            await tasks.stats_for_user(404)

    async def test_stats_count_only_the_users_tasks(
        self, tasks: TaskService, users: UserService, user_id: int
    ) -> None:
        other = await users.register(email="petr@example.com", name="Petr")
        assert other.id is not None
        await tasks.create(other.id, title="Not mine", description=None)
        first = await tasks.create(user_id, title="One", description=None)
        await tasks.create(user_id, title="Two", description=None)
        assert first.id is not None
        await tasks.change_status(first.id, TaskStatus.DONE)

        stats = await tasks.stats_for_user(user_id)

        assert stats.total == 2
        assert stats[TaskStatus.NEW] == 1
        assert stats[TaskStatus.DONE] == 1
