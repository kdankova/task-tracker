from http import HTTPStatus

from fastapi import APIRouter, HTTPException, Request

from app.api.errors import error_responses
from app.infrastructure.db.session import ping

router = APIRouter(tags=["health"])


@router.get("/health")
async def health() -> dict[str, str]:
    return {"status": "ok"}


@router.get("/ready", responses=error_responses(HTTPStatus.SERVICE_UNAVAILABLE))
async def ready(request: Request) -> dict[str, str]:
    try:
        await ping(request.app.state.engine)
    except Exception as exc:
        raise HTTPException(HTTPStatus.SERVICE_UNAVAILABLE, "Database is unavailable") from exc
    return {"status": "ok"}
