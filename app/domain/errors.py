class DomainError(Exception):
    pass


class UserNotFound(DomainError):
    def __init__(self, user_id: int) -> None:
        super().__init__(f"User {user_id} not found")


class TaskNotFound(DomainError):
    def __init__(self, task_id: int) -> None:
        super().__init__(f"Task {task_id} not found")


class EmailAlreadyTaken(DomainError):
    def __init__(self) -> None:
        super().__init__("A user with this email already exists")
