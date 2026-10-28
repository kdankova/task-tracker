from collections.abc import AsyncIterator
from contextlib import asynccontextmanager

from fastapi import FastAPI

from app.api.errors import register_error_handlers
from app.api.routers import health, tasks, users
from app.config import Settings, get_settings
from app.infrastructure.db.session import create_engine, create_session_factory


def create_app(settings: Settings | None = None) -> FastAPI:
    settings = settings or get_settings()
    engine = create_engine(settings.database_url)

    @asynccontextmanager
    async def lifespan(_: FastAPI) -> AsyncIterator[None]:
        yield
        await engine.dispose()

    app = FastAPI(
        title="Task Tracker",
        version="1.0.0",
        description="Users and their tasks",
        lifespan=lifespan,
    )
    app.state.engine = engine
    app.state.session_factory = create_session_factory(engine)

    register_error_handlers(app)
    app.include_router(users.router)
    app.include_router(tasks.router)
    app.include_router(health.router)
    return app


app = create_app()
