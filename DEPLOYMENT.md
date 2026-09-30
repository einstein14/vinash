# Deploying Vinash (FastAPI Cloud + PostgreSQL)

Vinash is designed to run behind HTTPS with a **shared PostgreSQL** database so multiple app instances see the same data for the same browser cookie.

## Architecture

```text
Browser  →  FastAPI Cloud (load balancer)
              ├── Instance A  →  PostgreSQL
              └── Instance B  →  PostgreSQL
```

Each browser holds a `vinash_anon` cookie. All thoughts are scoped to that anonymous user row in Postgres. Instances do not share local disk; only the database is shared.

## Prerequisites

- A PostgreSQL database (Neon, Supabase, RDS, etc.)
- Connection string using the **psycopg3** driver, for example:

  `postgresql+psycopg://USER:PASSWORD@HOST:5432/vinash`

## Environment variables

Set these in the FastAPI Cloud (or host) **secrets** UI — not in git.

| Variable | Production value |
|----------|------------------|
| `DATABASE_URL` | `postgresql+psycopg://...` (required) |
| `VINASH_ENV` | `production` (enables `Secure` cookies and hides OpenAPI) |
| `VINASH_COOKIE_NAME` | Optional; default `vinash_anon` |
| `VINASH_COOKIE_MAX_AGE` | Optional; default one year (seconds) |

If `DATABASE_URL` starts with `postgresql`, the app never falls back to SQLite.

## Deploy steps

1. **Connect the repo** to FastAPI Cloud (or your platform). Dependencies must include `fastapi[standard]` so the platform can run `fastapi run`. Entrypoint: `app.main:app` (see `[tool.fastapi]` in `pyproject.toml`).

2. **Add PostgreSQL** and copy the connection URL into `DATABASE_URL`. Use the `postgresql+psycopg://` form if your provider gives `postgresql://`.

3. **Run migrations** before or as part of the first deploy (one-time per environment):

   ```bash
   alembic upgrade head
   ```

   On FastAPI Cloud, run this via the platform’s shell/job or your CI step against the production `DATABASE_URL`.

4. **Set `VINASH_ENV=production`.**

5. **Deploy** and verify:

   - `GET /health` returns `{"status":"ok"}` (no PII).
   - Open the site, capture a thought, refresh — it persists.
   - Scale to **two instances** (if your plan allows): the same browser cookie should still see the same thoughts.

## Health check

Configure the load balancer to use:

- **Path:** `/health`
- **Expected:** HTTP 200, body `{"status":"ok"}`

`/health` does not require a cookie and does not touch thought content.

## Migrations

Schema changes are managed with Alembic under `alembic/versions/`. After pulling new code:

```bash
alembic upgrade head
```

Local SQLite and production Postgres use the same revision chain where possible.

## Security notes

- **No login:** isolation is cookie-based. Use HTTPS in production (`VINASH_ENV=production` sets `Secure` on the cookie).
- **Thought text** is not logged by the application.
- Cross-user access to a thought ID returns **404** (same as missing).
- **Delete all** is available at `/privacy` for the current cookie only.

## Local vs production

| | Local | Production |
|---|--------|------------|
| Database | SQLite file (`data/vinash.db`) | PostgreSQL |
| `VINASH_ENV` | `development` | `production` |
| Cookie `Secure` | off | on |
| Multiple instances | not supported (SQLite) | supported (Postgres) |

## Rollback

Keep database backups from your Postgres provider. To roll back application code, redeploy a previous revision; only run `alembic downgrade` if you understand the schema change being reversed.

## Checklist

- [ ] `DATABASE_URL` is PostgreSQL in secrets
- [ ] `VINASH_ENV=production`
- [ ] `alembic upgrade head` applied
- [ ] `/health` succeeds
- [ ] Capture thought → survives refresh
- [ ] Two instances (optional) → same cookie sees same data
- [ ] Different browsers/cookies → isolated journals
