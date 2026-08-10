# Stock check (branch-local)

Mobile stock-count app on HQ/SYP local servers. Posts invented `SA` / `3SA` bills into PARTS9 `SIMAS`+`SIDET` and updates `ICMAS.QTYOH2` on approve.

## Enable on a branch PC

```env
STOCK_CHECK_ENABLED=true
STOCK_CHECK_BRANCH=HQ
STOCK_CHECK_TOKEN_SECRET=long-random-shared-with-line-bot-host
STOCK_CHECK_APPROVER_LINE_USER_IDS=Uxxxx,Uyyyy
# Optional override; leave empty to auto-detect LAN IP each worker heartbeat
STOCK_CHECK_PUBLIC_BASE_URL=
STOCK_CHECK_LISTEN_PORT=8787
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

Worker heartbeats `public_base_url` automatically from the PC’s LAN IP (re-detected every heartbeat). Set `STOCK_CHECK_PUBLIC_BASE_URL` only if you need a fixed Tailscale/hostname URL.

Keep companion / Tiger Pay on:

```bat
run_tiger_pay.bat
```

(port **8000**). `run_dev.bat` is a deprecated alias for the same script.

Apply Supabase migration `20260811010000_worker_heartbeat_public_base_url.sql` so heartbeat can store `public_base_url`.

## LINE

Operators type `เช็คสต็อก`, `เช็กสตอก`, `เช็คของ`, `ตรวจนับสต็อก`, etc. Bot replies with HQ/SYP links from online worker heartbeats (`public_base_url` + signed token).

## Flow

Everyday **Take N** batch uses ABC + risk priority (see below).

1. Take N → leased pick list with LOCATION1/2 → open product → count  
2. Variance 0 → auto complete + audit mirror  
3. Variance ≠ 0 → pending draft → approver posts SA/3SA (fails clearly until writer login)  
4. End session releases unfinished leases  

### Everyday pick rules

1. **Candidates** — yesterday sales · negative stock · prior mismatch (`adjusted`) · prior SA/3SA · ABC cycle due · never counted  
2. **ABC** from 90-day **sales days** (exclude bill prefixes DN / TAR / TF / TFV / SA / 3SA): A≥30, B 10–29, C 1–9, N=0  
3. **Cycles** — A 21d · B 45d · C 90d · N only via risk / never pools  
4. **Repeat gap** — skip if counted within 14 days, unless negative stock (override)  
5. **Priority** (high→low) — negative → mismatch → SA history → yesterday → ABC due → never; one row per SKU  

Ondemand search supports typed BCODE/MCODE/PCODE **or photo upload** (same
server-side pyzbar decode as LINE camera / album scan). LIFF is not used.
