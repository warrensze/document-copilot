# Backend — Document Copilot

## Run

```bash
uv run uvicorn app.main:app --reload
```

## Migrations

```bash
uv run alembic upgrade head
uv run alembic revision --autogenerate -m "<description>"
```

## Test

```bash
uv run pytest
```

## Add deps

```bash
uv add <package>
```
