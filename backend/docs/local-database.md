# Local PostgreSQL

`compose.local.yaml` is for local development only and must be started explicitly.
Production connects directly to Neon using its own `DATABASE_URL`; it does not
run this Compose file or use the local credentials. The Python connection code
is shared between environments and only reads `DATABASE_URL`.

Run from `backend/`. Docker Compose starts PostgreSQL 17 on `127.0.0.1:5432`.
The local username, password and database name are all `lexical-learner`.

If port 5432 is occupied by the host PostgreSQL service, stop that service first
(on this machine: `sudo systemctl stop postgresql@17-main`). This leaves its
data intact but does not disable startup after a reboot.

```bash
docker compose -f compose.local.yaml up -d --wait
uv sync --locked
```

Copy `.env.example` to `.env` if `.env` does not already exist. Otherwise, add its
`DATABASE_URL` to your existing `.env`, preserving your Gemini settings.

```bash
uv run --env-file .env python -m lexical_learner.database
```

Expected output:

```text
('lexical-learner', 'lexical-learner')
```

The check connects through Psycopg and queries PostgreSQL without creating tables.
Use `postgresql://` for Psycopg; `postgresql+psycopg://` is a SQLAlchemy URL.
The database name can contain hyphens. Quote it as `"lexical-learner"` if using
it as an identifier in SQL.

To open psql or stop the container:

```bash
docker compose -f compose.local.yaml exec postgres psql -U lexical-learner -d lexical-learner
docker compose -f compose.local.yaml down
```

Data remains in the Docker volume `lexical_pgdata` after stopping the container.
These credentials are only for local development. Configure a separate
`DATABASE_URL` for Neon later.
