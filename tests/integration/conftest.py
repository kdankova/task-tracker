import os
from collections.abc import AsyncIterator
from pathlib import Path

import pytest
from alembic import command
from alembic.config import Config
from fastapi import FastAPI
from httpx import ASGITransport, AsyncClient
from sqlalchemy import make_url, text

from app.config import Settings
from app.main import create_app

TEST_DATABASE_URL = os.environ.get(
    "TEST_DATABASE_URL", "postgresql+asyncpg://postgres:postgres@localhost:5433/tasks_test"
)
ALEMBIC_INI = Path(__file__).parents[2] / "alembic.ini"


@pytest.fixture(scope="session", autouse=True)
def database_schema() -> None:
    database = make_url(TEST_DATABASE_URL).database or ""
    if not database.endswith("_test"):
        pytest.exit(f"Refusing to run tests against '{database}': name must end with '_test'")

    config = Config(ALEMBIC_INI)
    config.set_main_option("sqlalchemy.url", TEST_DATABASE_URL)
    command.downgrade(config, "base")
    command.upgrade(config, "head")


@pytest.fixture
async def app() -> AsyncIterator[FastAPI]:
    app = create_app(Settings(database_url=TEST_DATABASE_URL))
    async with app.state.engine.begin() as connection:
        await connection.execute(text("TRUNCATE users, tasks RESTART IDENTITY CASCADE"))
    yield app
    await app.state.engine.dispose()


@pytest.fixture
async def client(app: FastAPI) -> AsyncIterator[AsyncClient]:
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        yield client
