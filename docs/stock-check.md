# Stock check (branch-local)

Mobile stock-count app on HQ/SYP local servers. Posts invented `SA` / `3SA` bills into PARTS9 `SIMAS`+`SIDET` and updates `ICMAS.QTYOH2` on approve.

## Enable on a branch PC

```env
STOCK_CHECK_ENABLED=true
STOCK_CHECK_BRANCH=HQ
STOCK_CHECK_TOKEN_SECRET=long-random-shared-with-line-bot-host
STOCK_CHECK_APPROVER_LINE_USER_IDS=Uxxxx,Uyyyy
STOCK_CHECK_PUBLIC_BASE_URL=http://192.168.x.x:8787
POS_MSSQL_SERVER=KSS
POS_MSSQL_DATABASE=PARTS9
POS_MSSQL_USERNAME=python_reader
POS_MSSQL_PASSWORD=...
# Later:
# POS_MSSQL_WRITER_USERNAME=python_writer
# POS_MSSQL_WRITER_PASSWORD=...
WORKER_NAME=HQ-PC
```

Start **only** the stock-check server (does not run Tiger Pay / companion):

```bat
run_stock_check.bat
```

Listens on `STOCK_CHECK_LISTEN_PORT` (default **8787**). Routes under `/stock-check/`.

Keep companion / Tiger Pay on the usual:

```bat
run_dev.bat
```

(port **8000**).

Apply Supabase migration `20260811010000_worker_heartbeat_public_base_url.sql` so heartbeat can store `public_base_url`.

## LINE

Operators type `เช็คสต็อก` / `ตรวจนับสต็อก`. Bot replies with HQ/SYP links from online worker heartbeats (`public_base_url` + signed token).

## Flow

1. Take N → leased pick list with LOCATION1/2 → open product → count  
2. Variance 0 → auto complete + audit mirror  
3. Variance ≠ 0 → pending draft → approver posts SA/3SA (fails clearly until writer login)  
4. End session releases unfinished leases  

Ondemand search is for specific BCODE/MCODE/PCODE only.
