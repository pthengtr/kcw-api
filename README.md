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

### Companion UI

Thai-language shop UI at `/companion` (mobile-friendly):

- **ล่าสุด / วันนี้** — bill list mode (`GET /companion/bills?mode=latest|today`; overrides env `POS_BILLS_MODE` for that request)
- **ซ่อนสำเร็จ/ยกเลิกแล้ว** — hide settled Tiger attempts (default on)
- Send/Cancel buttons show loading while the request runs
- Timeline filters: คำขอ / ตอบกลับ / Webhook / โพลลิ่ง (color-coded), Bangkok timestamps, expandable payloads
- Preferences (mode, hide settled, timeline filters) persist in `localStorage`

### POS bill sources

Set in `.env`:

- `POS_BILL_SOURCE=mock` (default) — in-memory sample bills
- `POS_BILL_SOURCE=csv` — read SIMAS export CSV (good for testing)
- `POS_BILL_SOURCE=mssql` — query local SQL Server (`PARTS9` on `KSS`)

Shared cash-bill mapping (CSV and MSSQL):

- filter: `CASHED == Y`
- exclude bill numbers starting with `TF` or `TFV`
- `id` ← `ID`
- `bill_number` ← `BILLNO`
- `amount` ← `AFTERTAX`
- `pos_status` ← `PAID`
- `salesperson` ← `SALE`
- `POS_BILLS_MODE=latest` + `POS_BILLS_LIMIT=10` for testing
- `POS_BILLS_MODE=today` for same-day (MSSQL uses SQL Server `GETDATE()`)

#### CSV (testing)

```env
POS_BILL_SOURCE=csv
POS_BILLS_CSV_PATH=G:\Shared drives\KCW-Data\kcw_analytics\01_raw\raw_hq_simas_sales_bills.csv
POS_BILLS_MODE=latest
POS_BILLS_LIMIT=10
```

#### Local SQL Server (shop LAN)

Requires [ODBC Driver 17 for SQL Server](https://learn.microsoft.com/en-us/sql/connect/odbc/download-odbc-driver-for-sql-server) and `pyodbc` on the PC that runs the companion. Connection uses the same pattern as your notebook:

`mssql+pyodbc:///?odbc_connect=` + `quote_plus(DRIVER=...;SERVER=KSS;DATABASE=PARTS9;UID=python_reader;PWD=...;TrustServerCertificate=yes;)`

```env
POS_BILL_SOURCE=mssql
POS_MSSQL_SERVER=KSS
POS_MSSQL_DATABASE=PARTS9
POS_MSSQL_USERNAME=python_reader
POS_MSSQL_PASSWORD=xxxxx
POS_MSSQL_DRIVER=ODBC Driver 17 for SQL Server
# Bill-header table/view with CSV-equivalent columns (ID, BILLNO, AFTERTAX, ...)
POS_MSSQL_BILLS_TABLE=dbo.YourBillHeaderTable
POS_BILLS_MODE=today
POS_BILLS_LIMIT=50
```

Switch back to `POS_BILL_SOURCE=csv` anytime for offline testing without SQL Server.

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
