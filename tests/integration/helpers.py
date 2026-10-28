from itertools import count
from typing import Any

from httpx import AsyncClient, Response

_sequence = count(1)


def assert_error(response: Response, status: int, code: str) -> None:
    assert response.status_code == status, response.text
    assert response.json()["error"]["code"] == code


async def create_user(client: AsyncClient, **overrides: Any) -> dict[str, Any]:
    payload = {"email": f"user{next(_sequence)}@example.com", "name": "Ivan", **overrides}
    response = await client.post("/users", json=payload)
    assert response.status_code == 201, response.text
    body: dict[str, Any] = response.json()
    return body


async def create_task(client: AsyncClient, user_id: int, **overrides: Any) -> dict[str, Any]:
    payload = {"title": f"Task {next(_sequence)}", **overrides}
    response = await client.post(f"/users/{user_id}/tasks", json=payload)
    assert response.status_code == 201, response.text
    body: dict[str, Any] = response.json()
    return body


async def set_status(client: AsyncClient, task_id: int, status: str) -> Response:
    return await client.patch(f"/tasks/{task_id}/status", json={"status": status})
