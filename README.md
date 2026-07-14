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

On Windows, double-click or run:

```bat
run_dev.bat
```

This loads `.env`, creates `.venv` if needed, and starts uvicorn on port 8000.

Useful URLs:

- Companion UI: `http://127.0.0.1:8000/companion`
- Swagger: `http://127.0.0.1:8000/docs`
- Health: `http://127.0.0.1:8000/health`

## Tiger Pay companion (Phase 1)

Flow: POS bills → companion backend → Tiger Pay Open API
(`POST/GET/PUT /api/open/v2/payment...`). Status stays almost live via:

1. immediate API response
2. existing `POST /webhooks/tiger-pay` reconcile into `payment_attempt`
3. background polling of active attempts (every ~1.5s) when
   `TIGER_PAY_API_HOST` and `TIGER_PAY_CLIENT_ID` are set

### POS bill sources

Set in `.env`:

- `POS_BILL_SOURCE=mock` (default) — in-memory sample bills
- `POS_BILL_SOURCE=csv` — read SIMAS export CSV

CSV mapping (cash bills only):

- filter: `CASHED == Y`
- `id` ← `ID`
- `bill_number` ← `BILLNO`
- `amount` ← `AFTERTAX`
- `pos_status` ← `PAID`
- `salesperson` ← `SALE`
- `POS_BILLS_MODE=latest` + `POS_BILLS_LIMIT=10` for testing
- `POS_BILLS_MODE=today` for same-day production-shaped filtering

Example:

```env
POS_BILL_SOURCE=csv
POS_BILLS_CSV_PATH=G:\Shared drives\KCW-Data\kcw_analytics\01_raw\raw_hq_simas_sales_bills.csv
POS_BILLS_MODE=latest
POS_BILLS_LIMIT=10
```

### Supabase SQL (paste in SQL Editor)

Run the paste-ready script once:

[`docs/sql/tiger_pay_payment_attempt.sql`](docs/sql/tiger_pay_payment_attempt.sql)

It creates `tiger_pay.payment_attempt` and `tiger_pay.payment_event` with
duplicate-protection indexes. The same DDL is also in
`supabase/migrations/`.

### Companion env vars

Required for outbound Open API + polling:

- `TIGER_PAY_CLIENT_ID`
- `TIGER_PAY_CLIENT_SECRET`
- `TIGER_PAY_API_HOST` (include trailing slash, e.g. `http://192.168.1.50:8080/`)
- Postgres via existing `SUPABASE_DB_*` (companion reads/writes payment tables)

Optional:

- `TIGER_PAY_POLL_INTERVAL_SECONDS` (default `1.5`)

Frontend never calls Tiger Pay directly. Secrets stay server-side.

## Tiger Pay webhook

- Endpoint: `POST /webhooks/tiger-pay`
- Health check: `GET /health`

### Required Railway variables

- `TIGER_PAY_CLIENT_SECRET`
- `SUPABASE_URL`
- `SUPABASE_SERVICE_ROLE_KEY`

Optional:

- `TIGER_PAY_MAX_BODY_BYTES` (default `5242880`)
- `TIGER_PAY_CLIENT_ID` / `TIGER_PAY_API_HOST` (companion + poller)

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

## Cursor Cloud checks

See `docs/cloud-environment.md` for the Python 3.11 venv setup, app smoke
checks, Supabase CLI installation, migration commands, and the required secret
names for linking/running migrations.
