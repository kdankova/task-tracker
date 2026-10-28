# Task Tracker

Backend-сервис учёта задач пользователей.

**Стек:** Python 3.12, FastAPI, Pydantic v2, SQLAlchemy 2 (async), PostgreSQL 16, Alembic,
pytest, Docker Compose.

## Запуск

```bash
docker compose up --build
```

- API: http://localhost:8000
- Swagger: http://localhost:8000/docs

Миграции применяются автоматически при старте.

## Тесты

```bash
make test
```

Тесты запускаются в Docker на PostgreSQL. Локальный запуск (нужен [uv](https://docs.astral.sh/uv/)):

```bash
docker compose up -d db
uv sync
uv run pytest
```

Линтер и проверка типов: `make lint`, `make typecheck`.

## Переменные окружения

| Переменная | Назначение | По умолчанию |
|---|---|---|
| `DATABASE_URL` | подключение к БД | `postgresql+asyncpg://postgres:postgres@localhost:5433/tasks` |
| `TEST_DATABASE_URL` | БД для тестов | `postgresql+asyncpg://postgres:postgres@localhost:5433/tasks_test` |
| `POSTGRES_PORT` | порт PostgreSQL на хосте | `5433` |

Для `docker compose up` ничего настраивать не нужно. Пример — в [.env.example](.env.example).

## Архитектура

```
app/
├── domain/            сущности User и Task, статусы, доменные ошибки
├── application/       сервисы (сценарии) и интерфейсы репозиториев
├── infrastructure/db/ SQLAlchemy: модели, репозитории, транзакции
├── api/               FastAPI: роутеры, схемы, обработка ошибок
└── main.py            сборка приложения
migrations/            Alembic
tests/
├── unit/              доменная логика и сервисы без БД
└── integration/       HTTP API на PostgreSQL
```

Запрос проходит через `api` → `application` → `domain`. Сервисы работают с репозиториями
через интерфейсы, реализация на SQLAlchemy лежит в `infrastructure`. Ошибки домена
переводятся в HTTP-ответы в одном месте — `app/api/errors.py`.

Решения по вопросам, которые ТЗ не оговаривает, — в [ASSUMPTIONS.md](ASSUMPTIONS.md).

## API

| Метод | Путь | Описание |
|---|---|---|
| `POST` | `/users` | создать пользователя |
| `GET` | `/users/{user_id}` | получить пользователя |
| `POST` | `/users/{user_id}/tasks` | создать задачу |
| `GET` | `/users/{user_id}/tasks` | список задач (`status`, `limit`, `offset`) |
| `GET` | `/users/{user_id}/tasks/stats` | статистика по статусам |
| `PATCH` | `/tasks/{task_id}/status` | сменить статус |
| `DELETE` | `/tasks/{task_id}` | удалить задачу |

### Примеры

```bash
# Создать пользователя
curl -X POST localhost:8000/users \
  -H "Content-Type: application/json" \
  -d '{"email": "user@example.com", "name": "Ivan"}'
# 201 {"id": 1, "email": "user@example.com", "name": "Ivan", "created_at": "2026-06-05T12:00:00Z"}

# Получить пользователя
curl localhost:8000/users/1

# Создать задачу
curl -X POST localhost:8000/users/1/tasks \
  -H "Content-Type: application/json" \
  -d '{"title": "Подготовить отчет", "description": "Собрать данные за неделю"}'
# 201 {"id": 1, "user_id": 1, "title": "Подготовить отчет", "description": "Собрать данные за неделю",
#      "status": "new", "created_at": "...", "updated_at": "..."}

# Список задач с фильтром и пагинацией
curl "localhost:8000/users/1/tasks?status=new&limit=10&offset=0"
# 200 {"items": [...], "total": 1, "limit": 10, "offset": 0}

# Сменить статус
curl -X PATCH localhost:8000/tasks/1/status \
  -H "Content-Type: application/json" \
  -d '{"status": "in_progress"}'

# Статистика
curl localhost:8000/users/1/tasks/stats
# 200 {"total": 1, "new": 0, "in_progress": 1, "done": 0, "cancelled": 0}

# Удалить задачу
curl -X DELETE localhost:8000/tasks/1
# 200 {"ok": true}
```

### Ошибки

Все ошибки возвращаются в одном формате:

```json
{"error": {"code": "task_not_found", "message": "Task 42 not found"}}
```

| Код | HTTP | Когда |
|---|---|---|
| `validation_error` | 422 | некорректные данные запроса (подробности в `details`) |
| `user_not_found` | 404 | пользователь не найден |
| `task_not_found` | 404 | задача не найдена |
| `email_already_taken` | 409 | email уже занят |
| `internal_error` | 500 | непредвиденная ошибка |
