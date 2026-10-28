import asyncio
from datetime import datetime
from typing import Any

import pytest
from httpx import AsyncClient

from tests.integration.helpers import assert_error, create_user

MAX_BIGINT = 2**63 - 1


async def test_create_user(client: AsyncClient) -> None:
    response = await client.post("/users", json={"email": "user@example.com", "name": "Ivan"})

    assert response.status_code == 201
    body = response.json()
    assert body == {
        "id": body["id"],
        "email": "user@example.com",
        "name": "Ivan",
        "created_at": body["created_at"],
    }
    assert datetime.fromisoformat(body["created_at"]).tzinfo is not None


async def test_email_is_lowercased_and_name_trimmed(client: AsyncClient) -> None:
    user = await create_user(client, email="Ivan.Petrov@Example.COM", name="  Ivan  ")

    assert user["email"] == "ivan.petrov@example.com"
    assert user["name"] == "Ivan"


async def test_duplicate_email_is_rejected(client: AsyncClient) -> None:
    await create_user(client, email="user@example.com")

    response = await client.post("/users", json={"email": "user@example.com", "name": "Petr"})

    assert_error(response, 409, "email_already_taken")


async def test_duplicate_email_check_ignores_case(client: AsyncClient) -> None:
    await create_user(client, email="user@example.com")

    response = await client.post("/users", json={"email": "USER@Example.com", "name": "Petr"})

    assert_error(response, 409, "email_already_taken")


async def test_concurrent_registrations_with_same_email(client: AsyncClient) -> None:
    payload = {"email": "race@example.com", "name": "Ivan"}

    responses = await asyncio.gather(*(client.post("/users", json=payload) for _ in range(5)))

    assert sorted(response.status_code for response in responses) == [201, 409, 409, 409, 409]


@pytest.mark.parametrize(
    "payload",
    [
        pytest.param({"email": "not-an-email", "name": "Ivan"}, id="invalid-email"),
        pytest.param({"email": "user@example.com", "name": ""}, id="empty-name"),
        pytest.param({"email": "user@example.com", "name": "   "}, id="blank-name"),
        pytest.param({"email": "user@example.com", "name": "x" * 256}, id="name-too-long"),
        pytest.param({"name": "Ivan"}, id="missing-email"),
        pytest.param({"email": "user@example.com"}, id="missing-name"),
        pytest.param({"email": "user@example.com", "name": None}, id="null-name"),
        pytest.param({"email": "user@example.com", "name": "Ivan", "id": 7}, id="unknown-field"),
        pytest.param({"email": "user@example.com", "name": "Iv\u0000an"}, id="nul-in-name"),
    ],
)
async def test_invalid_user_payload(client: AsyncClient, payload: dict[str, Any]) -> None:
    response = await client.post("/users", json=payload)

    assert_error(response, 422, "validation_error")
    assert response.json()["error"]["details"]


async def test_validation_errors_do_not_echo_input(client: AsyncClient) -> None:
    response = await client.post("/users", json={"email": "secret-value", "name": "Ivan"})

    assert "secret-value" not in response.text


async def test_get_user(client: AsyncClient) -> None:
    user = await create_user(client)

    response = await client.get(f"/users/{user['id']}")

    assert response.status_code == 200
    assert response.json() == user


async def test_get_unknown_user(client: AsyncClient) -> None:
    response = await client.get("/users/999")

    assert_error(response, 404, "user_not_found")


@pytest.mark.parametrize("user_id", ["0", "-1", "abc", str(MAX_BIGINT + 1)])
async def test_get_user_with_invalid_id(client: AsyncClient, user_id: str) -> None:
    response = await client.get(f"/users/{user_id}")

    assert_error(response, 422, "validation_error")


async def test_get_user_with_max_id_is_not_found(client: AsyncClient) -> None:
    response = await client.get(f"/users/{MAX_BIGINT}")

    assert_error(response, 404, "user_not_found")
