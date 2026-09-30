# Vinash

Get it out of your head.

Vinash is a personal place to write down thoughts and, if you want, sort them later. It is a reflection and mental-clutter tool.

It is not a therapy app, a medical app, or a diagnostic tool. It does not treat anxiety, depression, ADHD, or any other condition.

## How your journal is tied to this browser

There is no signup. On your first visit, Vinash creates an anonymous ID and stores it in an **HttpOnly cookie** (`vinash_anon` by default). Your thoughts are saved in the database under that ID.

- **Same browser, same cookie** → same journal.
- **Clear cookies or use another browser** → a new empty journal (the old data stays in the database but is not linked to you without the cookie).
- **Anyone who has your cookie** can access that journal. There is no password recovery.

Use **Privacy** in the app to delete everything saved for your current browser.

## Local development

Vinash uses **SQLite** by default on your machine.

1. Copy environment defaults (optional):

   ```bash
   cp .env.example .env
   ```

2. Install and run:

   ```bash
   python3 -m venv .venv
   source .venv/bin/activate
   pip install -r requirements.txt
   # optional: pip install -r requirements-dev.txt
   uvicorn app.main:app --reload --host 127.0.0.1
   ```

3. Open [http://127.0.0.1:8000](http://127.0.0.1:8000).

The database file is created at `data/vinash.db` (from `DATABASE_URL=sqlite:///./data/vinash.db`). It is in `.gitignore`.

Keep `--host 127.0.0.1` for local use so other machines on your network cannot reach the app without you changing that on purpose.

### Schema migrations (local)

For a fresh SQLite file, tables are created on startup. To apply migrations explicitly (same as production):

```bash
alembic upgrade head
```

### Tests

```bash
source .venv/bin/activate
pip install -r requirements-dev.txt
pytest
```

Tests use a temporary SQLite database, not your `data/vinash.db`.

## Production

Production should use **shared PostgreSQL**, not SQLite, so multiple app instances can serve the same data.

Set `DATABASE_URL` to a PostgreSQL URL (for example `postgresql+psycopg://...`) and `VINASH_ENV=production` in your host’s secrets. See **[DEPLOYMENT.md](DEPLOYMENT.md)** for FastAPI Cloud, migrations, and health checks.

**Do not** point production at a SQLite file on disk if you run more than one instance.

## Features (this version)

Capture thoughts, inbox, sort a thought (action, revisit, keep, let go, resolved), actions list, revisit queue, weekly reflection counts (observational only), anonymous per-browser isolation, and delete-all for the current browser.

## Project layout

- `app/main.py` — app startup, middleware, static files
- `app/routes.py` — pages and form posts
- `app/queries.py` — database reads and writes (scoped by anonymous user)
- `app/db.py` — SQLAlchemy engine and sessions
- `app/models.py` — schema models
- `app/identity.py` — anonymous cookie middleware
- `app/config.py` — environment settings
- `alembic/` — database migrations
- `app/templates/` — HTML pages
