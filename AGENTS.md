# AGENTS.md

## Cursor Cloud specific instructions

### Overview

KCW API is a FastAPI backend that powers a LINE Messaging chatbot for a Thai auto-parts business. It connects to a Supabase-hosted PostgreSQL database, OpenAI for AI features, and the LINE Messaging API for bot interactions.

### Running the dev server

```bash
source /workspace/.venv/bin/activate
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

The server starts without valid external credentials; however, the `/line-webhook` endpoint will reject requests without a valid LINE signature, and database-backed features require real Supabase credentials.

### Testable without credentials

- `POST /kcw-peak/sync` — accepts any JSON body and echoes `{"status": "ok", "received": true}`.
- `GET /docs` — Swagger UI.

### Environment variables

A `.env` file (gitignored) is loaded via `python-dotenv`. Required variables are documented in `src/db/config.py` (Supabase DB), `src/bot/line_bot.py` (LINE), and `src/ai/openai_kb.py` (OpenAI + Supabase API). If credentials are missing, create a `.env` at the repo root with placeholder values; the server will start but external-service-dependent routes will fail at runtime.

For Cursor Cloud setup commands, Supabase CLI migration commands, and the full list of required secret names, see `docs/cloud-environment.md`. Use `.env.example` as a non-secret template and never commit real values.

### No tests or linting configured

This codebase has no test suite, no linting/formatting tools, and no pre-commit hooks. There is no `tests/` directory, no `pytest` in `requirements.txt`, and no ruff/flake8/black/mypy configuration.

### Python version

The project targets Python 3.11 (`runtime.txt`). The venv at `/workspace/.venv` should be built with Python 3.11 (installed from `ppa:deadsnakes/ppa` when the base image does not include it).

### Project structure

- `app/main.py` — FastAPI app with two POST endpoints: `/kcw-peak/sync` and `/line-webhook`.
- `src/` — all business logic: `db/` (SQLAlchemy + psycopg), `bot/` (LINE API helpers), `handlers/` (message routing, image handling), `ai/` (OpenAI KB), `access/` (user access control), `jobs/` (background worker), `search/`, `repos/`, `utils/`.
- `supabase/` — Supabase CLI config and SQL migrations.
- `notebooks/` — Jupyter notebooks for ad-hoc queries.
