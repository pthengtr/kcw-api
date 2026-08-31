# Transfer PARTS9 ledger (HQ↔SYP)

Operator inventory transfer — **not** bank transfer / โอนเงิน.

## Four document legs

| Direction | Ship (stock out) | Receive (stock in) |
|-----------|------------------|---------------------|
| **HQ → SYP** | **TF** HQ **SIMAS/SIDET** (KSS) | **TF** SYP **PIMAS/PIDET** (kss-pc) |
| **SYP → HQ** | **3TF** SYP **SIMAS/SIDET** (kss-pc) | **3TF** HQ **PIMAS/PIDET** (KSS) |

- Ship: positive `SIDET.QTY` on **SIMAS** (BILLTYPE 1). Stock direction is the sale leg, not a signed qty.
- Receive: positive `PIDET.QTY` on **PIMAS** (BILLTYPE 2). Stock direction is the purchase leg.
- **Not** like SA stock-check (`sa_writer`), which uses SI only and signs `SIDET.QTY` by BILLTYPE (+ out / − in).
- `ICMAS.QTYOH2` is updated explicitly on ship (−) and receive (+); line qty stays positive on both legs.
- `REMARKS` on ship: `TRF-{short_id}`; receive links ship bill via `REMARKS` / reference field (Phase 0 live sample).

## SQL grants

See `scripts/sql/grant_transfer_writer.sql` — SIMAS/SIDET + PIMAS/PIDET INSERT, ICMAS UPDATE on both KSS and kss-pc.
