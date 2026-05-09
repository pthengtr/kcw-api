# KCW API

Minimal FastAPI backend for KCW.

## Run locally

```bash
python3.11 -m venv /workspace/.venv
source /workspace/.venv/bin/activate
pip install -r requirements.txt
cp .env.example .env  # replace placeholders before using external services
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

## Cursor Cloud checks

See `docs/cloud-environment.md` for the Python 3.11 venv setup, app smoke
checks, Supabase CLI installation, migration commands, and the required secret
names for linking/running migrations.
