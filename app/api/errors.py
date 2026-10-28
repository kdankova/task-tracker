import logging
from collections.abc import Mapping
from http import HTTPStatus
from typing import Any

from fastapi import FastAPI, Request
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from starlette.exceptions import HTTPException

from app.api.schemas import ErrorBody, ErrorResponse
from app.domain.errors import (
    DomainError,
    EmailAlreadyTaken,
    TaskNotFound,
    UserNotFound,
)

logger = logging.getLogger(__name__)

_DOMAIN_ERRORS: dict[type[DomainError], tuple[HTTPStatus, str]] = {
    UserNotFound: (HTTPStatus.NOT_FOUND, "user_not_found"),
    TaskNotFound: (HTTPStatus.NOT_FOUND, "task_not_found"),
    EmailAlreadyTaken: (HTTPStatus.CONFLICT, "email_already_taken"),
}


def error_responses(*statuses: HTTPStatus) -> dict[int | str, dict[str, Any]]:
    return {status.value: {"model": ErrorResponse} for status in statuses}


def register_error_handlers(app: FastAPI) -> None:
    @app.exception_handler(DomainError)
    async def handle_domain_error(_: Request, exc: DomainError) -> JSONResponse:
        status, code = _DOMAIN_ERRORS[type(exc)]
        return _error_response(status, code, str(exc))

    @app.exception_handler(RequestValidationError)
    async def handle_validation_error(_: Request, exc: RequestValidationError) -> JSONResponse:
        details = [
            {"loc": list(error["loc"]), "msg": error["msg"], "type": error["type"]}
            for error in exc.errors()
        ]
        return _error_response(
            HTTPStatus.UNPROCESSABLE_ENTITY, "validation_error", "Invalid request", details
        )

    @app.exception_handler(HTTPException)
    async def handle_http_error(_: Request, exc: HTTPException) -> JSONResponse:
        status = HTTPStatus(exc.status_code)
        code = status.phrase.lower().replace(" ", "_")
        return _error_response(status, code, str(exc.detail), headers=exc.headers)

    @app.exception_handler(Exception)
    async def handle_unexpected_error(request: Request, _: Exception) -> JSONResponse:
        logger.exception("Unhandled error on %s %s", request.method, request.url.path)
        return _error_response(
            HTTPStatus.INTERNAL_SERVER_ERROR, "internal_error", "Internal server error"
        )


def _error_response(
    status: HTTPStatus,
    code: str,
    message: str,
    details: list[dict[str, Any]] | None = None,
    headers: Mapping[str, str] | None = None,
) -> JSONResponse:
    body = ErrorResponse(error=ErrorBody(code=code, message=message, details=details))
    return JSONResponse(
        status_code=status, content=body.model_dump(exclude_none=True), headers=headers
    )
