# Database Migrations (Alembic)

TokenFlow AI uses [Alembic](https://alembic.sqlalchemy.org/) for schema versioning.

## Setup

Alembic is already initialised in `backend/migrations/`. The `env.py` reads `DATABASE_URL` from your `.env` file automatically.

## Common commands

Run from the `backend/` directory:

```bash
# Apply all pending migrations (run this after pulling new code)
python -m alembic upgrade head

# Check current revision
python -m alembic current

# View migration history
python -m alembic history

# Generate a new migration after model changes
python -m alembic revision --autogenerate -m "describe_your_change"

# Roll back one migration
python -m alembic downgrade -1

# Roll back to a specific revision
python -m alembic downgrade <revision_id>
```

## Workflow for schema changes

1. Edit the SQLAlchemy model in `backend/app/models/`
2. Run `python -m alembic revision --autogenerate -m "your_description"`
3. Review the generated file in `migrations/versions/` — autogenerate is good but not perfect
4. Apply with `python -m alembic upgrade head`

## Development vs Production

- **Development**: `Base.metadata.create_all()` in the FastAPI lifespan handles fresh installs automatically. For incremental changes, run `alembic upgrade head`.
- **Production**: Always use `alembic upgrade head` only. Never use `create_all` directly in production.

## Current migrations

| Revision | Description |
|---|---|
| `4d20fec4e57d` | Baseline — users table, auth fields, UPSERT unique constraints, recommendation deduplication |
