from app.application.ports import UnitOfWork
from app.domain.entities import User
from app.domain.errors import UserNotFound


class UserService:
    def __init__(self, uow: UnitOfWork) -> None:
        self._uow = uow

    async def register(self, *, email: str, name: str) -> User:
        async with self._uow as uow:
            user = await uow.users.add(User.register(email=email, name=name))
            await uow.commit()
        return user

    async def get(self, user_id: int) -> User:
        async with self._uow as uow:
            user = await uow.users.get(user_id)
        if user is None:
            raise UserNotFound(user_id)
        return user
