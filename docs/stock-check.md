# Stock check (branch-local)

Mobile stock-count app on HQ/SYP local servers. Posts invented `SA` / `3SA` bills into PARTS9 `SIMAS`+`SIDET` and updates `ICMAS.QTYOH2` on approve.

## Enable on a branch PC

```env
STOCK_CHECK_ENABLED=true
STOCK_CHECK_BRANCH=HQ
STOCK_CHECK_TOKEN_SECRET=long-random-shared-with-line-bot-host
STOCK_CHECK_APPROVER_LINE_USER_IDS=Uxxxx,Uyyyy
# Idle seconds before unfinished leases return to pool (extended while counting)
STOCK_CHECK_LEASE_IDLE_SECONDS=300
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
run_stock_check.vbs
```

Or `run_stock_check.bat` directly. The bat is a **supervisor**: it restarts uvicorn if the process exits. Use `stop_stock_check.bat` to quit, `restart_stock_check.bat` to bounce uvicorn under the same supervisor. Prefer the `.vbs` so the process survives SSH disconnect.

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

Everyday **Take N** batch uses weighted ABC + risk pools (see below).

1. Take N → leased pick list with LOCATION1/2 + pool badge → open product → count  
2. Variance 0 → auto complete + audit mirror  
3. Variance ≠ 0 → pending draft → approver posts SA/3SA (fails clearly until writer login)  
4. **จบงาน** releases unfinished leases immediately  
5. Form submits show a full-screen busy spinner (blocks double-click)

### Lease idle (close tab vs still working)

Unfinished leases use an **idle timer**, not a hard walk deadline:

| Event | Effect |
|-------|--------|
| Take N / open queue / open product / save / skip | Extends idle window |
| Heartbeat every 60s on home (with queue) + product page | Extends while tab is visible |
| Close tab / kill WebView (no heartbeat) | SKUs return after idle window |
| จบงาน | Release now |

Default idle: **`STOCK_CHECK_LEASE_IDLE_SECONDS=300`** (5 minutes). Older `STOCK_CHECK_LEASE_TTL_SECONDS` is kept as a fallback alias.

### Everyday pick rules

1. **Candidates** — yesterday sales · negative stock · prior mismatch (`adjusted`) · prior SA/3SA · ABC cycle due · never counted  
2. **ABC** from 90-day **sales days** (exclude bill prefixes DN / TAR / TF / TFV / SA / 3SA): A≥30, B 10–29, C 1–9, N=0  
3. **Cycles** — A 21d · B 45d · C 90d · N only via risk / never pools  
4. **Repeat gap** — skip if counted within 14 days, unless negative stock (override)  
5. **Weighted Take N** — slots round-robin across 6 groups; list/fill order is **yesterday → ABC due → never → negative → mismatch → SA** (routine before risk). Short groups spill into later groups. One row per SKU; leases still claim the returned batch.  
6. **Walk bias** — soft-prefer same non-empty `LOCATION1` (blank bins sort last)  
7. **Pool badge** — each leased card shows group `1…6`; tap for Thai explanation dialog (also “กลุ่มงาน Take N คืออะไร?” on home)

| Pool | Name | Role |
|------|------|------|
| 4 | ขายเมื่อวาน | Routine — sold yesterday |
| 5 | รอบ ABC | Routine — ABC cycle due |
| 6 | ไม่เคยนับ | Routine — never counted here |
| 1 | ติดลบ | Risk — `QTYOH2 < 0` |
| 2 | ไม่ตรง | Risk — prior `adjusted` |
| 3 | เคย SA | Risk — prior SA/3SA |

Example Take **10** quotas: groups 4,5,6,1 → 2 each; 2,3 → 1 each.

### Do-not-restock (`QTYMIN`)

Legacy PARTS9 operators mark SKUs that should **not resurface on ICLOW / reorder** by setting **`ICMAS.QTYMIN = -1`** (any `QTYMIN < 0`).

Take N honors that:

- **Routine pools 4–6** — skip `QTYMIN < 0`  
- **Risk pools 1–3** — still include them (e.g. dead line with negative on-hand still gets cleaned)  
- Ondemand search / manual count is unchanged (operators can still open the SKU)

Do **not** confuse with `QTYOH2 < 0` (stock anomaly) — that stays a risk pick.

Ondemand search supports typed BCODE/MCODE/PCODE **or photo upload** (same
server-side pyzbar decode as LINE camera / album scan). LIFF is not used.
