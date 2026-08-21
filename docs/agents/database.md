# Database conventions

Load this file when touching models, migrations, or sessions. The data
model source of truth is `docs/concepts/data_model.md`.

## Stack

SQLAlchemy 2.0 (async, typed) + Alembic on SQLite in WAL mode. Single writer
process by design (one uvicorn worker) — do not add multi-process writes.

## Engine & sessions (when first models land)

- One async engine per process built from `Settings.database_path`:
  `sqlite+aiosqlite:///<path>`, `connect_args={"timeout": 30}` (busy timeout
  under WAL), `PRAGMA journal_mode=WAL` + `foreign_keys=ON` on connect.
- `async_sessionmaker(expire_on_commit=False)`; sessions via FastAPI
  dependency, commit in the dependency's exit, not inside handlers.
- Models: `Mapped[...]` / `mapped_column(...)` with explicit types, no
  bare `Column`. Reuse a naming_convention MetaData for constraint names so
  Alembic autogenerate produces stable names.

## Migrations (Alembic bootstrap)

Alembic is a declared dependency but the env isn't initialized yet. First
time:

```bash
uv run alembic init -t async alembic
# then wire alembic.ini -> src/brieftaube (env.py: import Base & settings,
# target_metadata = Base.metadata) and create the first migration.
```

Rules:

- Migrations are generated (`just db-revision "…"`), reviewed, and committed
  alongside the models that caused them — never hand-tuned away from
  autogenerate without a comment why.
- Migrations must be additive-first (expand/contract); SQLite ALTER is
  limited — batch operations (`op.batch_alter_table`) for column changes.
- `just db-upgrade` is idempotent; the app does NOT auto-migrate on boot.

## Testing

- Unit/integration tests use a throwaway SQLite file per test
  (`tmp_path`), schema created via `Base.metadata.create_all` (migrations
  themselves get one dedicated test that walks upgrade head on a fresh DB).
- Factories/fixtures build rows with sensible defaults; no shared mutable
  DB between tests.
- Timezone-aware datetimes everywhere (DTZ) — SQLite stores naive, models
  convert at the boundary via `DateTime(timezone=True)`.

## Performance

The load profile is trivial (single-digit users). Do not add caches,
connection pools tuning, or read replicas. One index per query the
escalation loop runs per tick is the ceiling of acceptable optimization.
