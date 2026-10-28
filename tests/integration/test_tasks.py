from datetime import datetime
from typing import Any

import pytest
from httpx import AsyncClient

from tests.integration.helpers import assert_error, create_task, create_user, set_status


@pytest.fixture
async def user_id(client: AsyncClient) -> int:
    user = await create_user(client)
    user_id: int = user["id"]
    return user_id


class TestCreateTask:
    async def test_create_task(self, client: AsyncClient, user_id: int) -> None:
        response = await client.post(
            f"/users/{user_id}/tasks",
            json={"title": "Подготовить отчет", "description": "Собрать данные за неделю"},
        )

        assert response.status_code == 201
        task = response.json()
        assert task["user_id"] == user_id
        assert task["title"] == "Подготовить отчет"
        assert task["description"] == "Собрать данные за неделю"
        assert task["status"] == "new"
        assert task["created_at"] == task["updated_at"]

    async def test_description_is_optional(self, client: AsyncClient, user_id: int) -> None:
        task = await create_task(client, user_id, title="No description")

        assert task["description"] is None

    async def test_blank_description_becomes_null(self, client: AsyncClient, user_id: int) -> None:
        task = await create_task(client, user_id, description="   ")

        assert task["description"] is None

    async def test_unknown_user(self, client: AsyncClient) -> None:
        response = await client.post("/users/999/tasks", json={"title": "Orphan"})

        assert_error(response, 404, "user_not_found")

    @pytest.mark.parametrize(
        "payload",
        [
            pytest.param({}, id="missing-title"),
            pytest.param({"title": ""}, id="empty-title"),
            pytest.param({"title": "   "}, id="blank-title"),
            pytest.param({"title": "x" * 256}, id="title-too-long"),
            pytest.param({"title": "Ok", "description": "x" * 10_001}, id="description-too-long"),
            pytest.param({"title": "Ok", "status": "done"}, id="status-is-not-client-settable"),
            pytest.param({"title": "a\u0000b"}, id="nul-in-title"),
            pytest.param({"title": "Ok", "description": "a\u0000b"}, id="nul-in-description"),
        ],
    )
    async def test_invalid_payload(
        self, client: AsyncClient, user_id: int, payload: dict[str, Any]
    ) -> None:
        response = await client.post(f"/users/{user_id}/tasks", json=payload)

        assert_error(response, 422, "validation_error")


class TestListTasks:
    async def test_lists_only_the_users_tasks_newest_first(
        self, client: AsyncClient, user_id: int
    ) -> None:
        first = await create_task(client, user_id)
        second = await create_task(client, user_id)
        other_user = await create_user(client)
        await create_task(client, other_user["id"])

        response = await client.get(f"/users/{user_id}/tasks")

        assert response.status_code == 200
        page = response.json()
        assert [task["id"] for task in page["items"]] == [second["id"], first["id"]]
        assert page["total"] == 2
        assert page["limit"] == 20
        assert page["offset"] == 0

    async def test_user_without_tasks(self, client: AsyncClient, user_id: int) -> None:
        response = await client.get(f"/users/{user_id}/tasks")

        assert response.json() == {"items": [], "total": 0, "limit": 20, "offset": 0}

    async def test_unknown_user(self, client: AsyncClient) -> None:
        response = await client.get("/users/999/tasks")

        assert_error(response, 404, "user_not_found")

    async def test_filter_by_status(self, client: AsyncClient, user_id: int) -> None:
        done = await create_task(client, user_id)
        await create_task(client, user_id)
        await set_status(client, done["id"], "done")
        other_user = await create_user(client)
        foreign = await create_task(client, other_user["id"])
        await set_status(client, foreign["id"], "done")

        response = await client.get(f"/users/{user_id}/tasks", params={"status": "done"})

        page = response.json()
        assert [task["id"] for task in page["items"]] == [done["id"]]
        assert page["total"] == 1

    async def test_filter_by_status_without_matches(
        self, client: AsyncClient, user_id: int
    ) -> None:
        await create_task(client, user_id)

        response = await client.get(f"/users/{user_id}/tasks", params={"status": "cancelled"})

        assert response.json()["items"] == []
        assert response.json()["total"] == 0

    async def test_invalid_status_filter(self, client: AsyncClient, user_id: int) -> None:
        response = await client.get(f"/users/{user_id}/tasks", params={"status": "archived"})

        assert_error(response, 422, "validation_error")

    async def test_pagination(self, client: AsyncClient, user_id: int) -> None:
        created = [await create_task(client, user_id) for _ in range(5)]
        newest_first = [task["id"] for task in reversed(created)]

        response = await client.get(f"/users/{user_id}/tasks", params={"limit": 2, "offset": 2})

        page = response.json()
        assert [task["id"] for task in page["items"]] == newest_first[2:4]
        assert page["total"] == 5
        assert page["limit"] == 2
        assert page["offset"] == 2

    async def test_offset_past_the_end(self, client: AsyncClient, user_id: int) -> None:
        await create_task(client, user_id)

        response = await client.get(f"/users/{user_id}/tasks", params={"offset": 10})

        assert response.json()["items"] == []
        assert response.json()["total"] == 1

    async def test_pagination_combined_with_filter(self, client: AsyncClient, user_id: int) -> None:
        in_progress_ids = []
        for _ in range(3):
            task = await create_task(client, user_id)
            await set_status(client, task["id"], "in_progress")
            in_progress_ids.append(task["id"])
        await create_task(client, user_id)

        response = await client.get(
            f"/users/{user_id}/tasks", params={"status": "in_progress", "limit": 2, "offset": 1}
        )

        page = response.json()
        newest_first = in_progress_ids[::-1]
        assert [task["id"] for task in page["items"]] == newest_first[1:3]
        assert {task["status"] for task in page["items"]} == {"in_progress"}
        assert page["total"] == 3

    @pytest.mark.parametrize(
        "params",
        [
            pytest.param({"limit": 0}, id="limit-zero"),
            pytest.param({"limit": 101}, id="limit-too-big"),
            pytest.param({"offset": -1}, id="negative-offset"),
            pytest.param({"offset": 2**63}, id="offset-overflows-bigint"),
            pytest.param({"limit": "ten"}, id="non-numeric-limit"),
        ],
    )
    async def test_invalid_pagination(
        self, client: AsyncClient, user_id: int, params: dict[str, Any]
    ) -> None:
        response = await client.get(f"/users/{user_id}/tasks", params=params)

        assert_error(response, 422, "validation_error")


class TestUpdateStatus:
    async def test_update_status(self, client: AsyncClient, user_id: int) -> None:
        task = await create_task(client, user_id)

        response = await set_status(client, task["id"], "in_progress")

        assert response.status_code == 200
        updated = response.json()
        assert updated["status"] == "in_progress"
        assert updated["created_at"] == task["created_at"]
        assert datetime.fromisoformat(updated["updated_at"]) > datetime.fromisoformat(
            task["updated_at"]
        )

    async def test_status_change_is_persisted(self, client: AsyncClient, user_id: int) -> None:
        task = await create_task(client, user_id)
        await set_status(client, task["id"], "done")

        response = await client.get(f"/users/{user_id}/tasks")

        assert response.json()["items"][0]["status"] == "done"

    async def test_same_status_is_idempotent(self, client: AsyncClient, user_id: int) -> None:
        task = await create_task(client, user_id)

        response = await set_status(client, task["id"], "new")

        assert response.status_code == 200
        assert response.json()["updated_at"] == task["updated_at"]

    @pytest.mark.parametrize("finished", ["done", "cancelled"])
    async def test_finished_task_can_be_reopened(
        self, client: AsyncClient, user_id: int, finished: str
    ) -> None:
        task = await create_task(client, user_id)
        await set_status(client, task["id"], finished)

        response = await set_status(client, task["id"], "in_progress")

        assert response.status_code == 200
        assert response.json()["status"] == "in_progress"

    async def test_unknown_task(self, client: AsyncClient) -> None:
        response = await set_status(client, 999, "done")

        assert_error(response, 404, "task_not_found")

    @pytest.mark.parametrize(
        "payload",
        [
            pytest.param({"status": "archived"}, id="unknown-status"),
            pytest.param({"status": "DONE"}, id="wrong-case"),
            pytest.param({"status": None}, id="null-status"),
            pytest.param({}, id="missing-status"),
            pytest.param({"status": "done", "title": "Renamed"}, id="unknown-field"),
        ],
    )
    async def test_invalid_payload(
        self, client: AsyncClient, user_id: int, payload: dict[str, Any]
    ) -> None:
        task = await create_task(client, user_id)

        response = await client.patch(f"/tasks/{task['id']}/status", json=payload)

        assert_error(response, 422, "validation_error")


class TestDeleteTask:
    async def test_delete_task(self, client: AsyncClient, user_id: int) -> None:
        task = await create_task(client, user_id)
        kept = await create_task(client, user_id)

        response = await client.delete(f"/tasks/{task['id']}")

        assert response.status_code == 200
        assert response.json() == {"ok": True}
        remaining = (await client.get(f"/users/{user_id}/tasks")).json()["items"]
        assert [item["id"] for item in remaining] == [kept["id"]]

    async def test_delete_twice(self, client: AsyncClient, user_id: int) -> None:
        task = await create_task(client, user_id)
        await client.delete(f"/tasks/{task['id']}")

        response = await client.delete(f"/tasks/{task['id']}")

        assert_error(response, 404, "task_not_found")

    async def test_deleted_task_cannot_be_updated(self, client: AsyncClient, user_id: int) -> None:
        task = await create_task(client, user_id)
        await client.delete(f"/tasks/{task['id']}")

        response = await set_status(client, task["id"], "done")

        assert_error(response, 404, "task_not_found")


class TestStats:
    async def test_stats(self, client: AsyncClient, user_id: int) -> None:
        statuses = ["new", "new", "in_progress", "done", "done", "done", "cancelled"]
        for status in statuses:
            task = await create_task(client, user_id)
            await set_status(client, task["id"], status)
        other_user = await create_user(client)
        await create_task(client, other_user["id"])

        response = await client.get(f"/users/{user_id}/tasks/stats")

        assert response.status_code == 200
        assert response.json() == {
            "total": 7,
            "new": 2,
            "in_progress": 1,
            "done": 3,
            "cancelled": 1,
        }

    async def test_stats_for_user_without_tasks(self, client: AsyncClient, user_id: int) -> None:
        response = await client.get(f"/users/{user_id}/tasks/stats")

        assert response.json() == {
            "total": 0,
            "new": 0,
            "in_progress": 0,
            "done": 0,
            "cancelled": 0,
        }

    async def test_stats_reflect_deletions(self, client: AsyncClient, user_id: int) -> None:
        task = await create_task(client, user_id)
        await create_task(client, user_id)
        await client.delete(f"/tasks/{task['id']}")

        response = await client.get(f"/users/{user_id}/tasks/stats")

        assert response.json()["total"] == 1

    async def test_unknown_user(self, client: AsyncClient) -> None:
        response = await client.get("/users/999/tasks/stats")

        assert_error(response, 404, "user_not_found")
