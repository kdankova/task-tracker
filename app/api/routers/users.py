from http import HTTPStatus

from fastapi import APIRouter

from app.api.dependencies import UserId, UserServiceDep
from app.api.errors import error_responses
from app.api.schemas import UserCreate, UserOut

router = APIRouter(prefix="/users", tags=["users"])


@router.post(
    "",
    status_code=HTTPStatus.CREATED,
    responses=error_responses(HTTPStatus.CONFLICT, HTTPStatus.UNPROCESSABLE_ENTITY),
)
async def create_user(payload: UserCreate, service: UserServiceDep) -> UserOut:
    user = await service.register(email=payload.email, name=payload.name)
    return UserOut.model_validate(user)


@router.get(
    "/{user_id}",
    responses=error_responses(HTTPStatus.NOT_FOUND, HTTPStatus.UNPROCESSABLE_ENTITY),
)
async def get_user(user_id: UserId, service: UserServiceDep) -> UserOut:
    user = await service.get(user_id)
    return UserOut.model_validate(user)
