# Transfer PARTS9 ledger (HQ↔SYP)

Operator inventory transfer — **not** bank transfer / โอนเงิน.

## Four document legs

| Direction | Ship (stock out) | Receive (stock in) |
|-----------|------------------|---------------------|
| **HQ → SYP** | **TF** HQ **SIMAS/SIDET** (KSS) | **TF** SYP **PIMAS/PIDET** (kss-pc) |
| **SYP → HQ** | **3TF** SYP **SIMAS/SIDET** (kss-pc) | **3TF** HQ **PIMAS/PIDET** (KSS) |

- Ship: negative `SIDET.QTY`, ICMAS `QTYOH2` decreases at source.
- Receive: positive `PIDET.QTY`, ICMAS `QTYOH2` increases at destination.
- `REMARKS` on ship: `TRF-{short_id}`; receive links ship bill via `REMARKS` / reference field (Phase 0 live sample).

## SQL grants

See `scripts/sql/grant_transfer_writer.sql` — SIMAS/SIDET + PIMAS/PIDET INSERT, ICMAS UPDATE on both KSS and kss-pc.
