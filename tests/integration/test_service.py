from httpx import AsyncClient

from tests.integration.helpers import assert_error


async def test_health(client: AsyncClient) -> None:
    response = await client.get("/health")

    assert response.json() == {"status": "ok"}


async def test_ready(client: AsyncClient) -> None:
    response = await client.get("/ready")

    assert response.json() == {"status": "ok"}


async def test_unknown_route_uses_the_common_error_format(client: AsyncClient) -> None:
    response = await client.get("/nowhere")

    assert_error(response, 404, "not_found")


async def test_wrong_method_uses_the_common_error_format(client: AsyncClient) -> None:
    response = await client.put("/users")

    assert_error(response, 405, "method_not_allowed")


async def test_openapi_schema_is_generated(client: AsyncClient) -> None:
    response = await client.get("/openapi.json")

    assert response.status_code == 200
    schemas = response.json()["components"]["schemas"]
    assert "ErrorResponse" in schemas
    assert "HTTPValidationError" not in schemas
