# AGENTS.md

## Cursor Cloud specific instructions

### Overview

KCW API is a FastAPI backend that powers a LINE Messaging chatbot for a Thai auto-parts business. It connects to a Supabase-hosted PostgreSQL database, OpenAI for AI features, and the LINE Messaging API for bot interactions.

Shared table/metric meaning lives in [kcw-docs dictionaries](https://github.com/pthengtr/kcw-docs/blob/main/dictionaries/README.md) (ICMAS, sales, PO, ICLOW, …).

### Running the dev server

```bash
source /workspace/.venv/bin/activate
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

The server can start without real external credentials if import-time placeholders are set for `OPENAI_API_KEY`, `SUPABASE_DB_URL`, and `SUPABASE_SERVICE_ROLE_KEY` (see `.env.example`). The `/line-webhook` endpoint will reject requests without a valid LINE signature, and database-backed or AI features require real Supabase/OpenAI credentials at runtime.

### Testable without credentials

- `POST /kcw-peak/sync` — accepts any JSON body and echoes `{"status": "ok", "received": true}`.
- `GET /docs` — Swagger UI.

### Environment variables

A `.env` file (gitignored) is loaded via `python-dotenv`. Required variables are documented in `src/db/config.py` (Supabase DB), `src/bot/line_bot.py` (LINE), and `src/ai/openai_kb.py` (OpenAI + Supabase API). If credentials are missing, create a `.env` at the repo root with placeholder values; the server will start but external-service-dependent routes will fail at runtime.

For Cursor Cloud setup commands, Supabase CLI migration commands, and the full list of required secret names, see `docs/cloud-environment.md`. Use `.env.example` as a non-secret template and never commit real values.

### Tests

`pytest` lives in `requirements.txt`. Tests are under `tests/` (Tiger Pay, stock-check, companion, worker preference). Not every route is covered.

### Python version

The project targets Python 3.11 (`runtime.txt`). The venv at `/workspace/.venv` should be built with Python 3.11 (installed from `ppa:deadsnakes/ppa` when the base image does not include it).

### Project structure

- `app/main.py` — FastAPI LINE webhook, Tiger Pay webhook, companion UI/API, printout.
- `app/stock_check_app.py` — separate stock-check LAN app (port 8787).
- `src/` — business logic: `db/`, `bot/`, `handlers/`, `ai/`, `access/`, `jobs/` (queue worker), `tiger_pay/`, `stock_check/`, `companion/`, `search/`, `repos/`.
- `supabase/` — Supabase CLI config and SQL migrations.
- `notebooks/` — Jupyter notebooks for ad-hoc queries.
