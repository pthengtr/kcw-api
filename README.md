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

## Tiger Pay webhook

- Endpoint: `POST /webhooks/tiger-pay`
- Health check: `GET /health`

### Required Railway variables

- `TIGER_PAY_CLIENT_SECRET`
- `SUPABASE_URL`
- `SUPABASE_SERVICE_ROLE_KEY`

Optional:

- `TIGER_PAY_MAX_BODY_BYTES` (default `5242880`)

### Railway deployment

- Start command: `uvicorn app.main:app --host 0.0.0.0 --port $PORT`
- Healthcheck path: `/health`
- `railway.toml` configures the healthcheck path for Railway deployments.

The webhook uses the Supabase service-role key server-side to call
`tiger_pay.ingest_webhook`. Never expose the service-role key to a frontend or
client application.

In Supabase, expose the `tiger_pay` schema (Dashboard → Settings → API → Exposed
Schemas) so the RPC can be called through the Supabase API.

Tiger Pay documentation mentions HMAC-SHA256 for the HTTP body in places, but the
vendor Node.js example hashes the raw request body with plain SHA-256. This
service follows the executable example.

### Tests

```bash
pytest
```

### Local webhook sender

```bash
export TIGER_PAY_CLIENT_SECRET=your-dev-secret
export TIGER_PAY_WEBHOOK_TEST_URL=http://127.0.0.1:8000/webhooks/tiger-pay
python scripts/send_tiger_pay_webhook.py
```

### Troubleshooting `Webhook processing failed` (HTTP 500)

This means JWT auth and payload validation succeeded, but the Supabase RPC step failed.

1. In Supabase Dashboard → **Settings → API → Exposed schemas**, add `tiger_pay`.
2. Confirm Railway `SUPABASE_URL` is the project API URL (`https://<ref>.supabase.co`), not the Postgres host.
3. Confirm Railway `SUPABASE_SERVICE_ROLE_KEY` is the **service role** key.
4. Check Railway logs for `error_category=supabase_rpc_failed` and `supabase_code=...`.
5. Run the direct RPC diagnostic:

```bash
export TIGER_PAY_CLIENT_SECRET=your-dev-secret
export SUPABASE_URL=https://<ref>.supabase.co
export SUPABASE_SERVICE_ROLE_KEY=your-service-role-key
python scripts/diagnose_tiger_pay_supabase.py
```

## Cursor Cloud checks

See `docs/cloud-environment.md` for the Python 3.11 venv setup, app smoke
checks, Supabase CLI installation, migration commands, and the required secret
names for linking/running migrations.
