# Initial substitute seed candidates (Phase 0)

## Glossary (locked)

| Operator says | Means here | Not |
|---------------|------------|-----|
| qtylo / L-1 / ไม่สั่งซ้ำ | `ICMAS.QTYMIN < 0` (usually `-1`), per branch | Out of stock (`QTYOH2 = 0`) |
| สินค้าทดแทน / แทน | Mutual peer SKUs in a catalog group | Bank transfer / โอนเงิน |
| REMARKS peers | Candidate signal only — not source of truth | Confirmed substitutes |

**Source:** Supabase mirrors `raw_kcw.raw_hq_icmas_products` / `raw_syp_icmas_products` (ingested ~2026-09-09). HQ is product master; branch `QTY*` stay per site.

**Status:** Human review required. Do not import until approved. Phase 1 builds empty CRUD first.

## Discovery counts

| Signal | Count |
|--------|------:|
| REMARKS substitute-like hits (HQ) | 223 |
| REMARKS with extractable peer BCODE | 152 directed links |
| REMARKS merged peer groups (≥2 BCODEs) | 133 |
| REMARKS hits without peer BCODE (incl. brand-order) | 71 (brand-order-ish ≈40) |
| PCODE clusters size 2–6 (clean, all HQ) | 4278 |
| MCODE clusters size 2–6 (clean, all HQ) | 3755 |
| PCODE L-1-relevant clusters scanned (cap 200) | 200 |
| MCODE L-1-relevant clusters scanned (cap 200) | 200 |
| PCODE groups proposed in this file | 40 |
| MCODE groups proposed in this file | 30 |
| HQ L-1 (`QTYMIN<0`) with SYP `QTYOH2>0` | 1522 |
| Proposed groups in this file | 203 |
| L-1+SYP-stock orphans (no peer in proposed groups) | 1487 (top 80 listed) |

## Open questions for reviewer

1. Should brand-order notes (e.g. “สั่งตราเพชรแทน”) become groups, or stay as purchasing notes only?
2. PCODE/MCODE twins of size 3–6 — often size/pack variants; default **reject** unless ops confirms mutual ship?
3. Prefer SYP-useful L-1 rows when approving first seed batch?

---

## Proposed groups

## Candidate group G001
- Confidence: med
- Evidence: REMARKS on 01050082: ใช้รหัส 01050076 แทน
- Evidence: REMARKS on 09050639: ใช้รหัส 01050076 แทน
- Evidence: REMARKS on 09050964: ใช้รหัส 01050076 แทน
- Members:
  - 01050076 — น็อตหัวเพลา (HQ QTYMIN=5, HQ QTYOH2=28, SYP QTYOH2=6)
  - 01050082 — น็อตหัวเพลา (HQ QTYMIN=-1, HQ QTYOH2=3, SYP QTYOH2=0)
  - 09050639 — สกรูหัวเพลา HINO (HQ QTYMIN=-1, HQ QTYOH2=2, SYP QTYOH2=0)
  - 09050964 — สกรูหัวเพลา HINO (HQ QTYMIN=-1, HQ QTYOH2=7, SYP QTYOH2=0)
- Notes: From ICMAS.REMARKS strong peer phrasing (HQ mirror).
- Reviewer action: approve / reject / edit members

## Candidate group G002
- Confidence: med
- Evidence: REMARKS on 12053041: 12053041=12052220  2300.- 10แถม1ของหมด13/8/69ใช้รหัส12052220แทน
- Evidence: REMARKS on 12052220: 12053041=1 ใช้ TK104 แทนได้ 12053301
- Evidence: REMARKS on 12052719: ใช้ 12053301 แทนได้ เหมือนกันเลย
- Members:
  - 12052220 — เก้าอี้เท้าแขน ดำ (HQ QTYMIN=3, HQ QTYOH2=10, SYP QTYOH2=0)
  - 12052719 — เก้าอี้เท้าแขน เหลือง (HQ QTYMIN=-1, HQ QTYOH2=1, SYP QTYOH2=0)
  - 12053041 — เก้าอี้เท้าแขน ดำ (HQ QTYMIN=-1, HQ QTYOH2=2, SYP QTYOH2=1)
  - 12053301 — เก้าอี้เท้าแขน ดำ จอนเดียร์ (HQ QTYMIN=-1, HQ QTYOH2=0, SYP QTYOH2=0)
- Notes: From ICMAS.REMARKS strong peer phrasing (HQ mirror).
- Reviewer action: approve / reject / edit members

## Candidate group G005
- Confidence: high
- Evidence: REMARKS on 08056897: ใช้รหัส08055531แทน
- Evidence: REMARKS on 08056245: ใช้รหัส08056897แทน
- Members:
  - 08055531 — ลูกรอก+ตัวดัน สพ.ไดชาร์ท (HQ QTYMIN=0, HQ QTYOH2=1, SYP QTYOH2=0)
  - 08056245 — ลูกรอก+ตัวดัน สพ.ไดชาร์ท (HQ QTYMIN=-1, HQ QTYOH2=0, SYP QTYOH2=0)
  - 08056897 — ลูกรอก+ตัวดัน สพ.ไดชาร์ท (HQ QTYMIN=-1, HQ QTYOH2=0, SYP QTYOH2=1)
- Notes: From ICMAS.REMARKS strong peer phrasing (HQ mirror).
- Reviewer action: approve / reject / edit members

## Candidate group G006
- Confidence: high
- Evidence: REMARKS on 13051912: -ใช้แทน D-Max ได้ ใช้หัวเก่า 13052397,12052169
- Evidence: REMARKS on 13052397: -ใช้แทน D-Max ได้ ใช้หัวเก่า ใช้13052169
- Members:
  - 13051912 — โอโตเมติกสตาร์ท (HQ QTYMIN=-1, HQ QTYOH2=0, SYP QTYOH2=0)
  - 13052169 — โอโตเมติกสตาร์ท (HQ QTYMIN=1, HQ QTYOH2=2, SYP QTYOH2=2)
  - 13052397 — โอโตเมติกสตาร์ท (HQ QTYMIN=0, HQ QTYOH2=1, SYP QTYOH2=0)
- Notes: From ICMAS.REMARKS strong peer phrasing (HQ mirror).
- Reviewer action: approve / reject / edit members

## Candidate group G007
- Confidence: high
- Evidence: REMARKS on 15014892: ใช้รหัสแทน 15014890
- Evidence: REMARKS on 15014891: VP ขาย 93.-6/62 ใช้แทน15014892/7PK 110.01.-
- Members:
  - 15014890 — ลูกปืน (HQ QTYMIN=-1, HQ QTYOH2=0, SYP QTYOH2=0)
  - 15014891 — ลูกปืน (HQ QTYMIN=4, HQ QTYOH2=12, SYP QTYOH2=8)
  - 15014892 — ลูกปืน ปลายเกียร์ M7040 (HQ QTYMIN=-1, HQ QTYOH2=0, SYP QTYOH2=0)
- Notes: From ICMAS.REMARKS strong peer phrasing (HQ mirror).
- Reviewer action: approve / reject / edit members

## Candidate group G008
- Confidence: high
- Evidence: REMARKS on 30010291: ขต.33010545+33010612/ของขาดยาวใช้ 30010444แทน
- Evidence: REMARKS on 30010526: ขต.33010545+33010612/ของขาดยาวใช้ 30010444แทน
- Members:
  - 30010291 — คอนโทรลวาวล์ ก.3/4" (HQ QTYMIN=-1, HQ QTYOH2=0, SYP QTYOH2=0)
  - 30010444 — คอนโทรลวาวล์ ก.3/4" (HQ QTYMIN=1, HQ QTYOH2=2, SYP QTYOH2=0)
  - 30010526 — คอนโทรลวาวล์ ก.3/4" 16NF (HQ QTYMIN=1, HQ QTYOH2=3, SYP QTYOH2=1)
- Notes: From ICMAS.REMARKS strong peer phrasing (HQ mirror).
- Reviewer action: approve / reject / edit members

## Candidate group G009
- Confidence: high
- Evidence: REMARKS on 30010351: ใช้ 30010476 แทน
- Evidence: REMARKS on 30010352: ใช้ 30010476 แทน
- Members:
  - 30010351 — ชุดแปลงเก้าอี้+ยาง+สกรู (HQ QTYMIN=-1, HQ QTYOH2=0, SYP QTYOH2=0)
  - 30010352 — ชุดแปลงเก้าอี้+ยาง+สกรู (HQ QTYMIN=-1, HQ QTYOH2=2, SYP QTYOH2=0)
  - 30010476 — ชุดแปลงเก้าอี้ (HQ QTYMIN=2, HQ QTYOH2=3, SYP QTYOH2=1)
- Notes: From ICMAS.REMARKS strong peer phrasing (HQ mirror).
- Reviewer action: approve / reject / edit members

## Candidate group G010
- Confidence: high
- Evidence: REMARKS on 30050484: CRRK 80.- ใช้รหัสแทน 30052567
- Evidence: REMARKS on 30051577: 33740-80290 ศูนย์ 590.-ใช้รหัส30052567แทนได้
- Members:
  - 30050484 — ซีลล้อหน้าคูโบต้า (HQ QTYMIN=-1, HQ QTYOH2=0, SYP QTYOH2=0)
  - 30051577 — ซีลตูด PTO คูโบต้า (HQ QTYMIN=1, HQ QTYOH2=2, SYP QTYOH2=1)
  - 30052567 — ซีลล้อหน้าคูโบต้า (HQ QTYMIN=4, HQ QTYOH2=0, SYP QTYOH2=1)
- Notes: From ICMAS.REMARKS strong peer phrasing (HQ mirror).
- Reviewer action: approve / reject / edit members

## Candidate group G011
- Confidence: high
- Evidence: REMARKS on 30051196: ใช้รหัส 30051193 แทน
- Evidence: REMARKS on 30051611: ใช้รหัส 30051193 แทนค่ะ
- Members:
  - 30051193 — สายไมล์ เกลียวรู 11,12 มิล (HQ QTYMIN=1, HQ QTYOH2=2, SYP QTYOH2=0)
  - 30051196 — สายไมล์  เกลียวรู 11มิล,12มิล (HQ QTYMIN=-1, HQ QTYOH2=1, SYP QTYOH2=1)
  - 30051611 — สายไมล์ ยาว 104.5 ซม. (HQ QTYMIN=-1, HQ QTYOH2=0, SYP QTYOH2=0)
- Notes: From ICMAS.REMARKS strong peer phrasing (HQ mirror).
- Reviewer action: approve / reject / edit members

## Candidate group G012
- Confidence: high
- Evidence: REMARKS on 30051365: เหมือน 30052066  ใช้แทน 30052067
- Evidence: REMARKS on 30052066: 5-07-112-06  ใช้แทนรหัส 30052067
- Members:
  - 30051365 — แหวนรองเพลาล้อหน้า (HQ QTYMIN=-1, HQ QTYOH2=0, SYP QTYOH2=0)
  - 30052066 — แผ่นชิมรองเฟืองขับหน้า (0.60) (HQ QTYMIN=-1, HQ QTYOH2=0, SYP QTYOH2=0)
  - 30052067 — แผ่นชิมรองเฟืองขับหน้า (0.80) (HQ QTYMIN=3, HQ QTYOH2=11, SYP QTYOH2=2)
- Notes: From ICMAS.REMARKS strong peer phrasing (HQ mirror).
- Reviewer action: approve / reject / edit members

## Candidate group G013
- Confidence: high
- Evidence: REMARKS on 30052110: ใช้รหัส 30052485 แทนคะ
- Evidence: REMARKS on 30052876: TC403-27560 สั่งสวนมะลิ ของหมด30/7/69 ใช้รหัส30052485แทน
- Members:
  - 30052110 — ซีลล้อหลังคูโบต้า (HQ QTYMIN=-1, HQ QTYOH2=0, SYP QTYOH2=0)
  - 30052485 — ซีลล้อหลังคูโบต้า (HQ QTYMIN=-1, HQ QTYOH2=10, SYP QTYOH2=6)
  - 30052876 — ซีลล้อหลังคูโบต้า L-1 (22-24 แรง) (HQ QTYMIN=1, HQ QTYOH2=2, SYP QTYOH2=2)
- Notes: From ICMAS.REMARKS strong peer phrasing (HQ mirror).
- Reviewer action: approve / reject / edit members

## Candidate group G015
- Confidence: high
- Evidence: REMARKS on 02051520: ใช้รหัส 02053453 แทนค่ะ
- Members:
  - 02051520 — ไส้กรองโซล่า เหล็ก ก.16NF (HQ QTYMIN=-1, HQ QTYOH2=0, SYP QTYOH2=0)
  - 02053453 — ไส้กรองโซล่า เหล็ก ก.16NF (HQ QTYMIN=2, HQ QTYOH2=4, SYP QTYOH2=2)
- Notes: From ICMAS.REMARKS strong peer phrasing (HQ mirror).
- Reviewer action: approve / reject / edit members

## Candidate group G016
- Confidence: high
- Evidence: REMARKS on 03011921: ใช้รหัส03012099แทนครับ
- Members:
  - 03011921 — ไส้กรองอากาศ แอร์ (HQ QTYMIN=-1, HQ QTYOH2=10, SYP QTYOH2=3)
  - 03012099 — กรองแอร์ ISUZU (HQ QTYMIN=4, HQ QTYOH2=8, SYP QTYOH2=?)
- Notes: From ICMAS.REMARKS strong peer phrasing (HQ mirror).
- Reviewer action: approve / reject / edit members

## Candidate group G017
- Confidence: high
- Evidence: REMARKS on 03012840: ใช้ 30050256 แทน
- Members:
  - 03012840 — จานคลัช 8"x10Tx25.6m (HQ QTYMIN=-1, HQ QTYOH2=0, SYP QTYOH2=0)
  - 30050256 — จานคลัช 8"x10Tx25.6m มีปริง (HQ QTYMIN=0, HQ QTYOH2=2, SYP QTYOH2=1)
- Notes: From ICMAS.REMARKS strong peer phrasing (HQ mirror).
- Reviewer action: approve / reject / edit members

## Candidate group G018
- Confidence: high
- Evidence: REMARKS on 03052532: พี่นกแจ้งว่าให้ใช้ 3ร่องใส่แทนได้เลย รหัส 03052531 ค่ะ
- Members:
  - 03052531 — มูเลย์ข้อเหวี่ยงหน้า 3ร่อง (HQ QTYMIN=0, HQ QTYOH2=1, SYP QTYOH2=1)
  - 03052532 — มูเลย์ข้อเหวี่ยงหน้า 2ร่อง (HQ QTYMIN=-1, HQ QTYOH2=0, SYP QTYOH2=0)
- Notes: From ICMAS.REMARKS strong peer phrasing (HQ mirror).
- Reviewer action: approve / reject / edit members

## Candidate group G019
- Confidence: high
- Evidence: REMARKS on 03054211: ใช้รหัส03054214แทน
- Members:
  - 03054211 — ยางหูแหนบหลังผ้าใบ (HQ QTYMIN=-1, HQ QTYOH2=0, SYP QTYOH2=0)
  - 03054214 — ยางหูแหนบหลังผ้าใบ (HQ QTYMIN=7, HQ QTYOH2=28, SYP QTYOH2=13)
- Notes: From ICMAS.REMARKS strong peer phrasing (HQ mirror).
- Reviewer action: approve / reject / edit members

## Candidate group G020
- Confidence: high
- Evidence: REMARKS on 03056615: ใช่รหัสนี้แทน03056613
- Members:
  - 03056613 — สายเพาเวอร์ ยาว 24 นิ้ว (HQ QTYMIN=0, HQ QTYOH2=2, SYP QTYOH2=1)
  - 03056615 — สายเพาเวอร์ (HQ QTYMIN=-1, HQ QTYOH2=0, SYP QTYOH2=0)
- Notes: From ICMAS.REMARKS strong peer phrasing (HQ mirror).
- Reviewer action: approve / reject / edit members

## Candidate group G021
- Confidence: high
- Evidence: REMARKS on 03056903: ใช้รหัส 03056900 แทนค่ะ
- Members:
  - 03056900 — ปะเก็นฝาวาว (HQ QTYMIN=1, HQ QTYOH2=4, SYP QTYOH2=2)
  - 03056903 — ปะเก็นฝาวาว 4JA (HQ QTYMIN=-1, HQ QTYOH2=0, SYP QTYOH2=0)
- Notes: From ICMAS.REMARKS strong peer phrasing (HQ mirror).
- Reviewer action: approve / reject / edit members

## Candidate group G022
- Confidence: high
- Evidence: REMARKS on 04019890: ใช้รหัส 04019893 แทนค่ะ // SKM 185.-/SMA 180.-
- Members:
  - 04019890 — กระจกมองข้าง ยาว (HQ QTYMIN=-1, HQ QTYOH2=0, SYP QTYOH2=0)
  - 04019893 — กระจกมองข้าง ยาว (HQ QTYMIN=1, HQ QTYOH2=2, SYP QTYOH2=2)
- Notes: From ICMAS.REMARKS strong peer phrasing (HQ mirror).
- Reviewer action: approve / reject / edit members

## Candidate group G025
- Confidence: high
- Evidence: REMARKS on 05015200: ใช้รหัส 05015202 แทน
- Members:
  - 05015200 — กระจกมองข้าง ดำ (HQ QTYMIN=-1, HQ QTYOH2=1, SYP QTYOH2=1)
  - 05015202 — กระจกมองข้าง ดำ (HQ QTYMIN=0, HQ QTYOH2=1, SYP QTYOH2=?)
- Notes: From ICMAS.REMARKS strong peer phrasing (HQ mirror).
- Reviewer action: approve / reject / edit members

## Candidate group G027
- Confidence: high
- Evidence: REMARKS on 07010524: 1540061003  ใช้รหัสแทน 07018661
- Members:
  - 07010524 — ไส้กรองเครื่อง เหล็ก ก. 1.5 (HQ QTYMIN=3, HQ QTYOH2=7, SYP QTYOH2=5)
  - 07018661 — ไส้กรองเครื่อง เหล็ก ก. 1.5 (HQ QTYMIN=-1, HQ QTYOH2=1, SYP QTYOH2=0)
- Notes: From ICMAS.REMARKS strong peer phrasing (HQ mirror).
- Reviewer action: approve / reject / edit members

## Candidate group G029
- Confidence: high
- Evidence: REMARKS on 07017410: 1644499128 /ใช้รหัส 07017413 แทนค่ะ
- Members:
  - 07017410 — ไส้กรองโซล่า ก.มิล 1.5 (HQ QTYMIN=-1, HQ QTYOH2=1, SYP QTYOH2=0)
  - 07017413 — ไส้กรองโซล่า ก.มิล 1.5 (HQ QTYMIN=1, HQ QTYOH2=2, SYP QTYOH2=2)
- Notes: From ICMAS.REMARKS strong peer phrasing (HQ mirror).
- Reviewer action: approve / reject / edit members

## Candidate group G030
- Confidence: high
- Evidence: REMARKS on 07051908: ราคา 3 ให้เฉพาะช่างเท่านั้นค่ะ ใช้รหัส07052194แทนครับ
- Members:
  - 07051908 — คอยล์เย็น (HQ QTYMIN=-1, HQ QTYOH2=1, SYP QTYOH2=0)
  - 07052194 — คอยล์เย็น (HQ QTYMIN=0, HQ QTYOH2=0, SYP QTYOH2=1)
- Notes: From ICMAS.REMARKS strong peer phrasing (HQ mirror).
- Reviewer action: approve / reject / edit members

## Candidate group G031
- Confidence: high
- Evidence: REMARKS on 07051914: ใช้รหัส 07052195แทน
- Members:
  - 07051914 — โบเวอร์/พัดลมแอร์ (HQ QTYMIN=-1, HQ QTYOH2=0, SYP QTYOH2=1)
  - 07052195 — โบเวอร์/พัดลมแอร์ (HQ QTYMIN=0, HQ QTYOH2=1, SYP QTYOH2=?)
- Notes: From ICMAS.REMARKS strong peer phrasing (HQ mirror).
- Reviewer action: approve / reject / edit members

## Candidate group G032
- Confidence: high
- Evidence: REMARKS on 08010030: E58-510016 STKG 260.-/ใช้รหัส08014874แทน
- Members:
  - 08010030 — เฟืองสตาร์ท แม่เหล็ก (HQ QTYMIN=-1, HQ QTYOH2=0, SYP QTYOH2=0)
  - 08014874 — เฟืองสตาร์ท แม่เหล็ก (HQ QTYMIN=0, HQ QTYOH2=1, SYP QTYOH2=1)
- Notes: From ICMAS.REMARKS strong peer phrasing (HQ mirror).
- Reviewer action: approve / reject / edit members

## Candidate group G033
- Confidence: high
- Evidence: REMARKS on 08010671: CKK  GMB  288- ใช้รหัส08014948แทน
- Members:
  - 08010671 — ลูกหมากคันชักสั้นT13 รู14m (HQ QTYMIN=-1, HQ QTYOH2=1, SYP QTYOH2=1)
  - 08014948 — ลูกหมากคันชักสั้นT13 รู14m (HQ QTYMIN=0, HQ QTYOH2=2, SYP QTYOH2=?)
- Notes: From ICMAS.REMARKS strong peer phrasing (HQ mirror).
- Reviewer action: approve / reject / edit members

## Candidate group G034
- Confidence: high
- Evidence: REMARKS on 08018280: ใช้รหัส08018281แทน
- Members:
  - 08018280 — ยางหูแหนบหลัง (HQ QTYMIN=-1, HQ QTYOH2=1, SYP QTYOH2=6)
  - 08018281 — ยางหูแหนบหลัง (HQ QTYMIN=5, HQ QTYOH2=20, SYP QTYOH2=?)
- Notes: From ICMAS.REMARKS strong peer phrasing (HQ mirror).
- Reviewer action: approve / reject / edit members

## Candidate group G035
- Confidence: high
- Evidence: REMARKS on 08054532: ใช้รหัส08056895แทน
- Members:
  - 08054532 — ลูกหมากปีกนกล่าง (HQ QTYMIN=-1, HQ QTYOH2=0, SYP QTYOH2=2)
  - 08056895 — ลูกหมากปีกนกล่าง (HQ QTYMIN=1, HQ QTYOH2=2, SYP QTYOH2=?)
- Notes: From ICMAS.REMARKS strong peer phrasing (HQ mirror).
- Reviewer action: approve / reject / edit members

## Candidate group G036
- Confidence: high
- Evidence: REMARKS on 08055323: ใช้รหัสแทน08056889
- Members:
  - 08055323 — ยางหูแหนบหลัง ล่าง สั้น (HQ QTYMIN=-1, HQ QTYOH2=10, SYP QTYOH2=6)
  - 08056889 — ยางหูแหนบหลัง ล่าง สั้น (HQ QTYMIN=7, HQ QTYOH2=0, SYP QTYOH2=?)
- Notes: From ICMAS.REMARKS strong peer phrasing (HQ mirror).
- Reviewer action: approve / reject / edit members

## Candidate group G038
- Confidence: high
- Evidence: REMARKS on 08056051: ใช้รหัส 08056797 แทน
- Members:
  - 08056051 — ปลั๊กท้ายราง (HQ QTYMIN=-1, HQ QTYOH2=0, SYP QTYOH2=2)
  - 08056797 — ปลั๊กท้ายราง (HQ QTYMIN=1, HQ QTYOH2=2, SYP QTYOH2=2)
- Notes: From ICMAS.REMARKS strong peer phrasing (HQ mirror).
- Reviewer action: approve / reject / edit members

## Candidate group G039
- Confidence: high
- Evidence: REMARKS on 08056076: ใช้ 08056783 แทน
- Members:
  - 08056076 — สายเบรคมือ หน้า (HQ QTYMIN=-1, HQ QTYOH2=0, SYP QTYOH2=1)
  - 08056783 — สายเบรคมือ หน้า (HQ QTYMIN=0, HQ QTYOH2=1, SYP QTYOH2=?)
- Notes: From ICMAS.REMARKS strong peer phrasing (HQ mirror).
- Reviewer action: approve / reject / edit members

## Candidate group G040
- Confidence: high
- Evidence: REMARKS on 08056195: ใช้รหัส08056871แทน
- Members:
  - 08056195 — แม่ปั้มเบรค 1"เสื้ออลูมิเนียม (HQ QTYMIN=-1, HQ QTYOH2=0, SYP QTYOH2=1)
  - 08056871 — แม่ปั้มเบรค 1" เสื้อเหล็ก (HQ QTYMIN=1, HQ QTYOH2=2, SYP QTYOH2=?)
- Notes: From ICMAS.REMARKS strong peer phrasing (HQ mirror).
- Reviewer action: approve / reject / edit members

## Candidate group G041
- Confidence: high
- Evidence: REMARKS on 11051619: MD370158 ยี่ห้อนี้ใส่ไม่เข้า ใช้รหัส 11052338 แทน
- Members:
  - 11051619 — แป๊บราวน้ำ/แป๊ปน้ำข้างเครื่อง (HQ QTYMIN=-1, HQ QTYOH2=0, SYP QTYOH2=0)
  - 11052338 — แป๊บราวน้ำ/แป๊ปน้ำข้างเครื่อง (HQ QTYMIN=0, HQ QTYOH2=1, SYP QTYOH2=1)
- Notes: From ICMAS.REMARKS strong peer phrasing (HQ mirror).
- Reviewer action: approve / reject / edit members

## Candidate group G042
- Confidence: high
- Evidence: REMARKS on 12010120: F1 950.- SCG 1100.- STKG 950.- SCGของหมดแล้วใช้รหัส12010601แทน
- Members:
  - 12010120 — ไดชาร์ท  12V (HQ QTYMIN=-1, HQ QTYOH2=0, SYP QTYOH2=0)
  - 12010601 — ไดชาร์ท  12V (HQ QTYMIN=1, HQ QTYOH2=5, SYP QTYOH2=1)
- Notes: From ICMAS.REMARKS strong peer phrasing (HQ mirror).
- Reviewer action: approve / reject / edit members

## Candidate group G043
- Confidence: high
- Evidence: REMARKS on 12010635: ใช้ 12010813 แทน
- Members:
  - 12010635 — ชาพก้าน STD (HQ QTYMIN=-1, HQ QTYOH2=1, SYP QTYOH2=1)
  - 12010813 — ชาพก้าน STD (HQ QTYMIN=0, HQ QTYOH2=3, SYP QTYOH2=1)
- Notes: From ICMAS.REMARKS strong peer phrasing (HQ mirror).
- Reviewer action: approve / reject / edit members

## Candidate group G044
- Confidence: high
- Evidence: REMARKS on 12010738: TSP-F3496/      ตุรกี ของหมดค่ะ    ใช้12010815 แทน
- Members:
  - 12010738 — แม่ปั้มคลัชบน (F028-1918) (HQ QTYMIN=-1, HQ QTYOH2=0, SYP QTYOH2=0)
  - 12010815 — แม่ปั้มคลัชบน (F028-1918) (HQ QTYMIN=1, HQ QTYOH2=2, SYP QTYOH2=1)
- Notes: From ICMAS.REMARKS strong peer phrasing (HQ mirror).
- Reviewer action: approve / reject / edit members

## Candidate group G048
- Confidence: high
- Evidence: REMARKS on 12052651: 5191547  KMP1250.- ใช้รหัสแทน 12051822
- Members:
  - 12051822 — ยอยกากบาทเพลาหน้านิวฮอลแลนด์ (HQ QTYMIN=1, HQ QTYOH2=0, SYP QTYOH2=2)
  - 12052651 — ยอยกากบาทเพลาหน้านิวฮอลแลนด์ (HQ QTYMIN=-1, HQ QTYOH2=0, SYP QTYOH2=0)
- Notes: From ICMAS.REMARKS strong peer phrasing (HQ mirror).
- Reviewer action: approve / reject / edit members

## Candidate group G049
- Confidence: high
- Evidence: REMARKS on 12052139: ใช้แทน 12053262
- Members:
  - 12052139 — ปริ้นตัว R (HQ QTYMIN=20, HQ QTYOH2=145, SYP QTYOH2=2)
  - 12053262 — ปริ้นตัว R (HQ QTYMIN=-1, HQ QTYOH2=10, SYP QTYOH2=0)
- Notes: From ICMAS.REMARKS strong peer phrasing (HQ mirror).
- Reviewer action: approve / reject / edit members

## Candidate group G053
- Confidence: high
- Evidence: REMARKS on 12052288: SMF ขาย 160.- 12/64 สินค้าหมด ใช้รหัส 12053393 แทน
- Members:
  - 12052288 — สวิทน้ำมันเครื่อง (HQ QTYMIN=-1, HQ QTYOH2=0, SYP QTYOH2=0)
  - 12053393 — สวิทน้ำมันเครื่อง (HQ QTYMIN=1, HQ QTYOH2=0, SYP QTYOH2=1)
- Notes: From ICMAS.REMARKS strong peer phrasing (HQ mirror).
- Reviewer action: approve / reject / edit members

## Candidate group G054
- Confidence: high
- Evidence: REMARKS on 12052676: ใช้ 12052407 แทนได้
- Members:
  - 12052407 — จานไถพรวน 26" คมนอก (HQ QTYMIN=8, HQ QTYOH2=21, SYP QTYOH2=7)
  - 12052676 — จานไถพรวน 26"  (ใช้ 12052407) (HQ QTYMIN=-1, HQ QTYOH2=0, SYP QTYOH2=7)
- Notes: From ICMAS.REMARKS strong peer phrasing (HQ mirror).
- Reviewer action: approve / reject / edit members

## Candidate group G055
- Confidence: high
- Evidence: REMARKS on 12052873: PB 450.- ไม่มีน็อตแถมใช้รหัสนี้แทน12053279
- Members:
  - 12052873 — ปลอกต่อเฟืองเพลากลาง (HQ QTYMIN=-1, HQ QTYOH2=0, SYP QTYOH2=1)
  - 12053279 — ปลอกต่อเพลาทรานเฟอร์ (HQ QTYMIN=1, HQ QTYOH2=3, SYP QTYOH2=1)
- Notes: From ICMAS.REMARKS strong peer phrasing (HQ mirror).
- Reviewer action: approve / reject / edit members

## Candidate group G057
- Confidence: high
- Evidence: REMARKS on 12053036: SKKS หมด/KCY,SAE,SMF,P.T ไม่มี/ใช้รหัส12053700แทน
- Members:
  - 12053036 — ชุดกรองโซล่า เดี่ยว (HQ QTYMIN=-1, HQ QTYOH2=0, SYP QTYOH2=0)
  - 12053700 — ชุดกรองโซล่าเดี่ยว ประกอบเสร็จ (HQ QTYMIN=0, HQ QTYOH2=2, SYP QTYOH2=1)
- Notes: From ICMAS.REMARKS strong peer phrasing (HQ mirror).
- Reviewer action: approve / reject / edit members

## Candidate group G058
- Confidence: high
- Evidence: REMARKS on 12053061: 4 แฉกของหมด ใช้รหัส 12053065 6 แฉกแทนค่ะ
- Members:
  - 12053061 — จานคลัชจอนเดียร์ 4แฉก (HQ QTYMIN=-1, HQ QTYOH2=0, SYP QTYOH2=0)
  - 12053065 — จานคลัช 6แฉก 11"19Tx35MM. สปริง (HQ QTYMIN=-1, HQ QTYOH2=1, SYP QTYOH2=1)
- Notes: From ICMAS.REMARKS strong peer phrasing (HQ mirror).
- Reviewer action: approve / reject / edit members

## Candidate group G060
- Confidence: high
- Evidence: REMARKS on 12053793: SKKS 4700.- ใช้ 12053934 แทน
- Members:
  - 12053793 — แผ่นรองเฟืองขับดุม (ฝาดุม) (HQ QTYMIN=-1, HQ QTYOH2=0, SYP QTYOH2=1)
  - 12053934 — ฝาปิดดุมล้อหน้า M16X50 ก.1.5 (HQ QTYMIN=0, HQ QTYOH2=2, SYP QTYOH2=?)
- Notes: From ICMAS.REMARKS strong peer phrasing (HQ mirror).
- Reviewer action: approve / reject / edit members

## Candidate group G061
- Confidence: high
- Evidence: REMARKS on 12053867: CAR65704 ใช้ 12053933 แทน
- Members:
  - 12053867 — เฟืองบายสี+เดือยหมู 10x32 (HQ QTYMIN=-1, HQ QTYOH2=0, SYP QTYOH2=1)
  - 12053933 — เฟืองบายสี+เดือยหมู 10x32 (HQ QTYMIN=0, HQ QTYOH2=1, SYP QTYOH2=?)
- Notes: From ICMAS.REMARKS strong peer phrasing (HQ mirror).
- Reviewer action: approve / reject / edit members

## Candidate group G062
- Confidence: high
- Evidence: REMARKS on 30052305: ยางปากกระบอก+ยางลูกสูบ ใช้รหัส 12053886 แทน
- Members:
  - 12053886 — ชุดซ่อมกระบอกช่วยยก UHS45 (HQ QTYMIN=1, HQ QTYOH2=3, SYP QTYOH2=1)
  - 30052305 — ชุดซ่อมกระบอกใบมีดหน้า (HQ QTYMIN=-1, HQ QTYOH2=0, SYP QTYOH2=0)
- Notes: From ICMAS.REMARKS strong peer phrasing (HQ mirror).
- Reviewer action: approve / reject / edit members

## Candidate group G064
- Confidence: high
- Evidence: REMARKS on 13051289: 78882-90180/      S.PRY 80.-/SMA 70.-/PIT หมด 52.-ใช้รหัส13010881แทน
- Members:
  - 13010881 — พลาสติกตูดกรองดักน้ำ (HQ QTYMIN=2, HQ QTYOH2=14, SYP QTYOH2=3)
  - 13051289 — พลาสติกตูดกรองดักน้ำ (HQ QTYMIN=-1, HQ QTYOH2=0, SYP QTYOH2=0)
- Notes: From ICMAS.REMARKS strong peer phrasing (HQ mirror).
- Reviewer action: approve / reject / edit members

## Candidate group G065
- Confidence: high
- Evidence: REMARKS on 13013013: UNP 65.- ใช้รหัส13011852แทนครับ
- Members:
  - 13011852 — ลูกดูดโอโต (HQ QTYMIN=1, HQ QTYOH2=3, SYP QTYOH2=0)
  - 13013013 — ลูกดูดโอโต (HQ QTYMIN=-1, HQ QTYOH2=0, SYP QTYOH2=1)
- Notes: From ICMAS.REMARKS strong peer phrasing (HQ mirror).
- Reviewer action: approve / reject / edit members

## Candidate group G066
- Confidence: high
- Evidence: REMARKS on 13012649: ใช้รหัส 13013195 เป็นตัว 2 น็อตแทน
- Members:
  - 13012649 — ไดเออร์ (HQ QTYMIN=-1, HQ QTYOH2=0, SYP QTYOH2=0)
  - 13013195 — ไดเออร์ (HQ QTYMIN=0, HQ QTYOH2=5, SYP QTYOH2=1)
- Notes: From ICMAS.REMARKS strong peer phrasing (HQ mirror).
- Reviewer action: approve / reject / edit members

## Candidate group G067
- Confidence: high
- Evidence: REMARKS on 13012658: ใช้รหัส13013317แทน
- Members:
  - 13012658 — สวิทเพรชเชอร์ (HQ QTYMIN=-1, HQ QTYOH2=0, SYP QTYOH2=1)
  - 13013317 — สวิทเพรชเชอร์ (HQ QTYMIN=0, HQ QTYOH2=0, SYP QTYOH2=1)
- Notes: From ICMAS.REMARKS strong peer phrasing (HQ mirror).
- Reviewer action: approve / reject / edit members

## Candidate group G069
- Confidence: high
- Evidence: REMARKS on 35010126: หมดไม่สั้่ง ใช้13013144 แทน
- Members:
  - 13013144 — ปั้มติ๊ก BOSCH ขาตรง (HQ QTYMIN=5, HQ QTYOH2=33, SYP QTYOH2=3)
  - 35010126 — ปั้มติ๊ก / ปั้มน้ำมันเชื้อเพลิง (HQ QTYMIN=-1, HQ QTYOH2=0, SYP QTYOH2=0)
- Notes: From ICMAS.REMARKS strong peer phrasing (HQ mirror).
- Reviewer action: approve / reject / edit members

## Candidate group G070
- Confidence: high
- Evidence: REMARKS on 13016842: ใช้รหัส13016844แทน
- Members:
  - 13016842 — สายพาน (HQ QTYMIN=-1, HQ QTYOH2=0, SYP QTYOH2=0)
  - 13016844 — สายพาน (HQ QTYMIN=1, HQ QTYOH2=2, SYP QTYOH2=2)
- Notes: From ICMAS.REMARKS strong peer phrasing (HQ mirror).
- Reviewer action: approve / reject / edit members

## Candidate group G072
- Confidence: high
- Evidence: REMARKS on 13034175: ใช้รหัส13050415แทนครับ
- Members:
  - 13034175 — หลอดไฟฮาโลเจน แฉก (HQ QTYMIN=-1, HQ QTYOH2=4, SYP QTYOH2=5)
  - 13050415 — หลอดไฟฮาโลเจน (HQ QTYMIN=10, HQ QTYOH2=25, SYP QTYOH2=3)
- Notes: From ICMAS.REMARKS strong peer phrasing (HQ mirror).
- Reviewer action: approve / reject / edit members

## Candidate group G073
- Confidence: high
- Evidence: REMARKS on 13051315: ของส่วนตัว มีรูป/ใช้รหัส13034844แทน
- Members:
  - 13034844 — ฟิวส์เมนเสียบใหญ่ ขาตรง (HQ QTYMIN=2, HQ QTYOH2=2, SYP QTYOH2=2)
  - 13051315 — ฟิวส์เมนขาแยก (HQ QTYMIN=-1, HQ QTYOH2=4, SYP QTYOH2=1)
- Notes: From ICMAS.REMARKS strong peer phrasing (HQ mirror).
- Reviewer action: approve / reject / edit members

## Candidate group G074
- Confidence: high
- Evidence: REMARKS on 13036006: ใช้ H8 แทนได้ รหัส 13052492
- Members:
  - 13036006 — หลอดไฟ H11 (HQ QTYMIN=-1, HQ QTYOH2=0, SYP QTYOH2=0)
  - 13052492 — หลอดไฟฮาโลเจน (HQ QTYMIN=-1, HQ QTYOH2=4, SYP QTYOH2=4)
- Notes: From ICMAS.REMARKS strong peer phrasing (HQ mirror).
- Reviewer action: approve / reject / edit members

## Candidate group G075
- Confidence: high
- Evidence: REMARKS on 13037532: C7HSA (ใช้รหัส13037534แทน)
- Members:
  - 13037532 — หัวเทียนมอเตอร์ไซด์ (HQ QTYMIN=-1, HQ QTYOH2=0, SYP QTYOH2=0)
  - 13037534 — หัวเทียนมอเตอร์ไซด์ (HQ QTYMIN=-1, HQ QTYOH2=11, SYP QTYOH2=1)
- Notes: From ICMAS.REMARKS strong peer phrasing (HQ mirror).
- Reviewer action: approve / reject / edit members

## Candidate group G076
- Confidence: high
- Evidence: REMARKS on 13050686: ใช้รหัส 13052692 แทน
- Members:
  - 13050686 — คัทเอาท์ตะกร้อ ND 12V. (HQ QTYMIN=-1, HQ QTYOH2=1, SYP QTYOH2=2)
  - 13052692 — คัทเอาท์ตะกร้อ ND 12V. (HQ QTYMIN=0, HQ QTYOH2=2, SYP QTYOH2=?)
- Notes: From ICMAS.REMARKS strong peer phrasing (HQ mirror).
- Reviewer action: approve / reject / edit members

## Candidate group G078
- Confidence: high
- Evidence: REMARKS on 14050087: SUG ไม่ได้จำหน่ายแล้ว ใช้รหัส 14010559 แทน
- Members:
  - 14010559 — ใบหินเจียร์ 4นิ้ว (HQ QTYMIN=25, HQ QTYOH2=45, SYP QTYOH2=28)
  - 14050087 — ใบหินเจียร์ 4นิ้ว (HQ QTYMIN=-1, HQ QTYOH2=-25, SYP QTYOH2=0)
- Notes: From ICMAS.REMARKS strong peer phrasing (HQ mirror).
- Reviewer action: approve / reject / edit members

## Candidate group G079
- Confidence: high
- Evidence: REMARKS on 15010544: SYB ขาย 230.-/VP 197.-/ใช้รหัสนี้แทน15017741
- Members:
  - 15010544 — ลูกปืนคลัช 40m นูน (HQ QTYMIN=-1, HQ QTYOH2=0, SYP QTYOH2=0)
  - 15017741 — ลูกปืนคลัช 40m นูน (HQ QTYMIN=1, HQ QTYOH2=2, SYP QTYOH2=2)
- Notes: From ICMAS.REMARKS strong peer phrasing (HQ mirror).
- Reviewer action: approve / reject / edit members

## Candidate group G081
- Confidence: high
- Evidence: REMARKS on 15011555: ใช้รหัส 15010577 แทน
- Members:
  - 15010577 — ลูกปืน (HQ QTYMIN=0, HQ QTYOH2=2, SYP QTYOH2=1)
  - 15011555 — ลูกปืน 3307 (HQ QTYMIN=-1, HQ QTYOH2=0, SYP QTYOH2=0)
- Notes: From ICMAS.REMARKS strong peer phrasing (HQ mirror).
- Reviewer action: approve / reject / edit members

## Candidate group G083
- Confidence: high
- Evidence: REMARKS on 30050282: ใช้รหัส 15017442 แทน เบอร์51107 08401-51107
- Members:
  - 15017442 — ลูกปืนกันรุน (รับนน.M9540) (HQ QTYMIN=1, HQ QTYOH2=2, SYP QTYOH2=3)
  - 30050282 — ลูกปืนรับน้ำหนัก/ลูกปืนกันรุนเพลาตั้ง (HQ QTYMIN=-1, HQ QTYOH2=0, SYP QTYOH2=0)
- Notes: From ICMAS.REMARKS strong peer phrasing (HQ mirror).
- Reviewer action: approve / reject / edit members

## Candidate group G084
- Confidence: high
- Evidence: REMARKS on 15017643: SYB 245.-/KOYO 7VP 197.-/ใช้รหัส15017645แทน
- Members:
  - 15017643 — ลูกปืนคลัช หน้าเรียบ (HQ QTYMIN=-1, HQ QTYOH2=1, SYP QTYOH2=1)
  - 15017645 — ลูกปืนคลัช หน้าเรียบ (HQ QTYMIN=0, HQ QTYOH2=1, SYP QTYOH2=?)
- Notes: From ICMAS.REMARKS strong peer phrasing (HQ mirror).
- Reviewer action: approve / reject / edit members

## Candidate group G085
- Confidence: high
- Evidence: REMARKS on 30052577: 35533-43380 / ใช้รหัส 15050654 แทนค่ะ
- Members:
  - 15050654 — ลูกปืนกันรุน / เพลาตั้ง M105-108 / รับน้ำหนัก M9000 (HQ QTYMIN=1, HQ QTYOH2=0, SYP QTYOH2=2)
  - 30052577 — ลูกปืนกันรุน / เพลาตั้ง M105-108 / รับน้ำหนัก M9000 (HQ QTYMIN=-1, HQ QTYOH2=0, SYP QTYOH2=0)
- Notes: From ICMAS.REMARKS strong peer phrasing (HQ mirror).
- Reviewer action: approve / reject / edit members

## Candidate group G087
- Confidence: high
- Evidence: REMARKS on 16052746: ใช้รหัสนี้แทน16052747
- Members:
  - 16052746 — ปลั๊กคอยล์ (HQ QTYMIN=-1, HQ QTYOH2=0, SYP QTYOH2=1)
  - 16052747 — ปลั๊กคอยล์ (HQ QTYMIN=1, HQ QTYOH2=3, SYP QTYOH2=1)
- Notes: From ICMAS.REMARKS strong peer phrasing (HQ mirror).
- Reviewer action: approve / reject / edit members

## Candidate group G088
- Confidence: high
- Evidence: REMARKS on 22050341: ใช้รหัส22050149แทน
- Members:
  - 22050149 — หัวเชื้อล้างหัวฉีดดีเซล (HQ QTYMIN=5, HQ QTYOH2=8, SYP QTYOH2=8)
  - 22050341 — หัวเชื้อล้างหัวฉีดดีเซล (HQ QTYMIN=-1, HQ QTYOH2=?, SYP QTYOH2=?)
- Notes: From ICMAS.REMARKS strong peer phrasing (HQ mirror).
- Reviewer action: approve / reject / edit members

## Candidate group G089
- Confidence: high
- Evidence: REMARKS on 22050276: 30E27131616/SAE 730.-/NH610A ใช้ 22050318แทน
- Members:
  - 22050276 — น้ำมันเบรค (HQ QTYMIN=-1, HQ QTYOH2=0, SYP QTYOH2=0)
  - 22050318 — น้ำมันเบรค สีดำ รถไถฟอร์ด (HQ QTYMIN=1, HQ QTYOH2=0, SYP QTYOH2=3)
- Notes: From ICMAS.REMARKS strong peer phrasing (HQ mirror).
- Reviewer action: approve / reject / edit members

## Candidate group G090
- Confidence: high
- Evidence: REMARKS on 31050798: ใช้รหัส 25020100 แทน
- Members:
  - 25020100 — ยางโอริง (HQ QTYMIN=1, HQ QTYOH2=5, SYP QTYOH2=4)
  - 31050798 — ยางรอบเกียร์ (HQ QTYMIN=-1, HQ QTYOH2=0, SYP QTYOH2=0)
- Notes: From ICMAS.REMARKS strong peer phrasing (HQ mirror).
- Reviewer action: approve / reject / edit members

## Candidate group G091
- Confidence: high
- Evidence: REMARKS on 30010045: ใช้35010482แทนครับ
- Members:
  - 30010045 — ปั้มน้ำ+หน้าแปลน (HQ QTYMIN=-1, HQ QTYOH2=0, SYP QTYOH2=0)
  - 35010482 — ปั้มน้ำ C190 (HQ QTYMIN=1, HQ QTYOH2=3, SYP QTYOH2=1)
- Notes: From ICMAS.REMARKS strong peer phrasing (HQ mirror).
- Reviewer action: approve / reject / edit members

## Candidate group G095
- Confidence: high
- Evidence: REMARKS on 30050026: ใช้ 30052969 แทน
- Members:
  - 30050026 — จานกดคลัชคูโบต้า 11นิ้ว (HQ QTYMIN=-1, HQ QTYOH2=0, SYP QTYOH2=0)
  - 30052969 — จานกดคลัชคูโบต้า 11 นิ้ว (HQ QTYMIN=1, HQ QTYOH2=2, SYP QTYOH2=1)
- Notes: From ICMAS.REMARKS strong peer phrasing (HQ mirror).
- Reviewer action: approve / reject / edit members

## Candidate group G097
- Confidence: high
- Evidence: REMARKS on 30050181: 20 แถม 1 จ๋าให้ -1 แล้วใช้ยาว 3.1/2" รหัส 30053022 แทน
- Members:
  - 30050181 — สลักแขนลาก 6x3" (HQ QTYMIN=-1, HQ QTYOH2=1, SYP QTYOH2=0)
  - 30053022 — สลักแขนลาก 6x3.1/2" (HQ QTYMIN=2, HQ QTYOH2=20, SYP QTYOH2=5)
- Notes: From ICMAS.REMARKS strong peer phrasing (HQ mirror).
- Reviewer action: approve / reject / edit members

## Candidate group G098
- Confidence: high
- Evidence: REMARKS on 30050913: ใช้รหัส 30050188 แทนค่ะ
- Members:
  - 30050188 — สลักตัวยูต่อโซ่+ปริ้นตัว R (HQ QTYMIN=4, HQ QTYOH2=5, SYP QTYOH2=4)
  - 30050913 — สลักตัวยูต่อโซ่คูโบต้า (HQ QTYMIN=-1, HQ QTYOH2=0, SYP QTYOH2=0)
- Notes: From ICMAS.REMARKS strong peer phrasing (HQ mirror).
- Reviewer action: approve / reject / edit members

## Candidate group G100
- Confidence: high
- Evidence: REMARKS on 30050283: ใช้รหัสนี้แทน 35010475
- Evidence: REMARKS on 35010475: ใช้แทนรหัส30050283 ใช้ด้วยกันได้
- Members:
  - 30050283 — ไส้กรองอากาศคูโบต้า (HQ QTYMIN=-1, HQ QTYOH2=0, SYP QTYOH2=0)
  - 35010475 — กรองอากาศอิเซกิ (HQ QTYMIN=2, HQ QTYOH2=5, SYP QTYOH2=3)
- Notes: From ICMAS.REMARKS strong peer phrasing (HQ mirror).
- Reviewer action: approve / reject / edit members

## Candidate group G101
- Confidence: high
- Evidence: REMARKS on 30052467: ใช้รหัส 30050350 แทน หมดไม่สั่ง
- Members:
  - 30050350 — แขนกลางคูโบต้า แป๊ปใหญ่ (HQ QTYMIN=4, HQ QTYOH2=5, SYP QTYOH2=2)
  - 30052467 — แขนกลางคูโบต้า เล็ก (HQ QTYMIN=-1, HQ QTYOH2=2, SYP QTYOH2=0)
- Notes: From ICMAS.REMARKS strong peer phrasing (HQ mirror).
- Reviewer action: approve / reject / edit members

## Candidate group G103
- Confidence: high
- Evidence: REMARKS on 30050595: ใช้กับรุ่น Kx191-3   ใช้รหัสแทน 30052531
- Members:
  - 30050595 — ชาพก้าน STD (HQ QTYMIN=-1, HQ QTYOH2=0, SYP QTYOH2=0)
  - 30052531 — ชาพก้าน STD (HQ QTYMIN=5, HQ QTYOH2=12, SYP QTYOH2=4)
- Notes: From ICMAS.REMARKS strong peer phrasing (HQ mirror).
- Reviewer action: approve / reject / edit members

## Candidate group G105
- Confidence: high
- Evidence: REMARKS on 30050659: .ใช้รหัสแทน 30052552
- Members:
  - 30050659 — ดุมล้อหน้า คูโบต้า (HQ QTYMIN=-1, HQ QTYOH2=0, SYP QTYOH2=0)
  - 30052552 — ดุมล้อหน้า คูโบต้า (HQ QTYMIN=1, HQ QTYOH2=3, SYP QTYOH2=1)
- Notes: From ICMAS.REMARKS strong peer phrasing (HQ mirror).
- Reviewer action: approve / reject / edit members

## Candidate group G106
- Confidence: high
- Evidence: REMARKS on 30050720: TC650-26350 // VP ไม่มี มีแต่ของจีน // MKV 675.-/ใช้รหัส30053184แทน
- Members:
  - 30050720 — ลูกปืนคลัชคูโบต้า (HQ QTYMIN=-1, HQ QTYOH2=0, SYP QTYOH2=0)
  - 30053184 — ลูกปืนคลัชคูโบต้า (HQ QTYMIN=6, HQ QTYOH2=20, SYP QTYOH2=7)
- Notes: From ICMAS.REMARKS strong peer phrasing (HQ mirror).
- Reviewer action: approve / reject / edit members

## Candidate group G109
- Confidence: high
- Evidence: REMARKS on 30051142: ใช้รหัส30052534แทนครับต่างกันที่หัวอัดจารบีแต่ใช้ได้
- Members:
  - 30051142 — ชุดยอยเพลากลาง (13Tx14) (HQ QTYMIN=-1, HQ QTYOH2=0, SYP QTYOH2=0)
  - 30052534 — ชุดง่ามยอยเพลากลาง (13Tx14) (HQ QTYMIN=2, HQ QTYOH2=3, SYP QTYOH2=1)
- Notes: From ICMAS.REMARKS strong peer phrasing (HQ mirror).
- Reviewer action: approve / reject / edit members

## Candidate group G111
- Confidence: high
- Evidence: REMARKS on 30051363: ใช้รหัสแทน 30051304
- Members:
  - 30051304 — แหวนรองลูกปืน (HQ QTYMIN=-1, HQ QTYOH2=0, SYP QTYOH2=0)
  - 30051363 — แผ่นชิมเพลาตั้ง (HQ QTYMIN=2, HQ QTYOH2=6, SYP QTYOH2=1)
- Notes: From ICMAS.REMARKS strong peer phrasing (HQ mirror).
- Reviewer action: approve / reject / edit members

## Candidate group G112
- Confidence: high
- Evidence: REMARKS on 30051625: ใช้รหัส 30051563 แทนค่ะ
- Members:
  - 30051563 — ยางลูกสูบคลัช/โอริงเสื้อคลัช เล็ก (HQ QTYMIN=1, HQ QTYOH2=5, SYP QTYOH2=2)
  - 30051625 — ยางเหลี่ยมวาวคลัช/โอริงเสื้อคลัช เล็ก (HQ QTYMIN=-1, HQ QTYOH2=0, SYP QTYOH2=0)
- Notes: From ICMAS.REMARKS strong peer phrasing (HQ mirror).
- Reviewer action: approve / reject / edit members

## Candidate group G113
- Confidence: high
- Evidence: REMARKS on 30051675: -BM8000,PB8000.- SKKS7500- ใช้แทน 30051687
- Members:
  - 30051675 — ปั้มไฮโดรลิค (15T) เสื้อเหล็ก (HQ QTYMIN=0, HQ QTYOH2=1, SYP QTYOH2=1)
  - 30051687 — ปั้มไฮโดรลิค (15T) เสื้ออลู (HQ QTYMIN=-1, HQ QTYOH2=0, SYP QTYOH2=0)
- Notes: From ICMAS.REMARKS strong peer phrasing (HQ mirror).
- Reviewer action: approve / reject / edit members

## Candidate group G117
- Confidence: high
- Evidence: REMARKS on 30052082: ใช้รหัส 30052842 แทนค่ะ
- Members:
  - 30052082 — ซีลรูดฝุ่น (HQ QTYMIN=-1, HQ QTYOH2=0, SYP QTYOH2=0)
  - 30052842 — ซีลรูดฝุ่น (HQ QTYMIN=0, HQ QTYOH2=0, SYP QTYOH2=3)
- Notes: From ICMAS.REMARKS strong peer phrasing (HQ mirror).
- Reviewer action: approve / reject / edit members

## Candidate group G120
- Confidence: high
- Evidence: REMARKS on 30052735: 30052749 ใช้รหัสนี้แทน
- Members:
  - 30052735 — ซีล/ปะเก็นลูกสูบกระบอกช่วยเลี้ยว (HQ QTYMIN=-1, HQ QTYOH2=1, SYP QTYOH2=0)
  - 30052749 — ซีล/ปะเก็นลูกสูบกระบอกช่วยเลี้ยว (HQ QTYMIN=0, HQ QTYOH2=4, SYP QTYOH2=1)
- Notes: From ICMAS.REMARKS strong peer phrasing (HQ mirror).
- Reviewer action: approve / reject / edit members

## Candidate group G124
- Confidence: high
- Evidence: REMARKS on 32010118: ใช้รหัส 32010122 แทนค่ะ
- Members:
  - 32010118 — กรองน้ำมันเครื่อง 12UNF-2B (HQ QTYMIN=-1, HQ QTYOH2=1, SYP QTYOH2=0)
  - 32010122 — กรองน้ำมันเครื่อง 12UNF-2B (HQ QTYMIN=1, HQ QTYOH2=2, SYP QTYOH2=1)
- Notes: From ICMAS.REMARKS strong peer phrasing (HQ mirror).
- Reviewer action: approve / reject / edit members

## Candidate group G125
- Confidence: high
- Evidence: REMARKS on 32050165: ใช้รหัส 32050317 แทนค่ะ
- Members:
  - 32050165 — ไส้กรองอากาศ มีจาน (HQ QTYMIN=-1, HQ QTYOH2=0, SYP QTYOH2=0)
  - 32050317 — ไส้กรองอากาศ มีจาน (HQ QTYMIN=0, HQ QTYOH2=1, SYP QTYOH2=1)
- Notes: From ICMAS.REMARKS strong peer phrasing (HQ mirror).
- Reviewer action: approve / reject / edit members

## Candidate group G126
- Confidence: high
- Evidence: REMARKS on 35010473: SMA 430.-ปี65 16546-05H10/ใช้รหัส32050209แทน
- Members:
  - 32050209 — ไส้กรองอากาศ มีใบพัด (HQ QTYMIN=0, HQ QTYOH2=2, SYP QTYOH2=1)
  - 35010473 — กรองอากาศอิเซกิ มีใบพัด (HQ QTYMIN=-1, HQ QTYOH2=0, SYP QTYOH2=1)
- Notes: From ICMAS.REMARKS strong peer phrasing (HQ mirror).
- Reviewer action: approve / reject / edit members

## Candidate group G127
- Confidence: high
- Evidence: REMARKS on 35010061: ใช้แทน 35010057
- Members:
  - 35010057 — พลาสติก+ยางกระบอกไฮ (HQ QTYMIN=1, HQ QTYOH2=1, SYP QTYOH2=1)
  - 35010061 — พลาสติกกระบอกไฮ ตัวล่าง (HQ QTYMIN=-1, HQ QTYOH2=0, SYP QTYOH2=0)
- Notes: From ICMAS.REMARKS strong peer phrasing (HQ mirror).
- Reviewer action: approve / reject / edit members

## Candidate group G128
- Confidence: high
- Evidence: REMARKS on 35010371: CRRK ใช้ 35010536 แทน
- Members:
  - 35010371 — สกรูล้อหลัง(สตัท)ครบชุด (HQ QTYMIN=-1, HQ QTYOH2=0, SYP QTYOH2=4)
  - 35010536 — สกรูล้อหลัง(สตัท)ครบชุด (HQ QTYMIN=4, HQ QTYOH2=6, SYP QTYOH2=4)
- Notes: From ICMAS.REMARKS strong peer phrasing (HQ mirror).
- Reviewer action: approve / reject / edit members

## Candidate group G129
- Confidence: high
- Evidence: REMARKS on 35050248: 52623109/PB 3,500.- CRRK 3,000.-ใช้รหัส35010403แทน
- Members:
  - 35010403 — หม้อน้ำ อลูมิเนียมทั้งใบ (HQ QTYMIN=1, HQ QTYOH2=4, SYP QTYOH2=1)
  - 35050248 — หม้อน้ำ YANMA พลาสติก (สูง 375cm,กว้าง 440cm) (HQ QTYMIN=-1, HQ QTYOH2=4, SYP QTYOH2=0)
- Notes: From ICMAS.REMARKS strong peer phrasing (HQ mirror).
- Reviewer action: approve / reject / edit members

## Candidate group G004
- Confidence: high
- Evidence: REMARKS on 03052283: แยกไปเป็นรหัส 35050089 แทน
- Evidence: REMARKS on 35050089: ราคาเก่า280.-   ใช้รหัส03053418แทน
- Members:
  - 03052283 — แหวนลูกสูบ 86มิล (HQ QTYMIN=-1, HQ QTYOH2=0, SYP QTYOH2=0)
  - 03053418 — แหวนลูกสูบ 86M รุ่น4แหวน (HQ QTYMIN=-1, HQ QTYOH2=0, SYP QTYOH2=0)
  - 35050089 — แหวนลูกสูบ 86 มิล (HQ QTYMIN=-1, HQ QTYOH2=0, SYP QTYOH2=0)
- Notes: From ICMAS.REMARKS strong peer phrasing (HQ mirror).
- Reviewer action: approve / reject / edit members

## Candidate group G026
- Confidence: high
- Evidence: REMARKS on 05051934: ใช้รหัส05051441แทน
- Members:
  - 05051441 — แม่ปั้มเบรค (HQ QTYMIN=0, HQ QTYOH2=1, SYP QTYOH2=?)
  - 05051934 — แม่ปั้มเบรค 15/16" (HQ QTYMIN=-1, HQ QTYOH2=1, SYP QTYOH2=0)
- Notes: From ICMAS.REMARKS strong peer phrasing (HQ mirror).
- Reviewer action: approve / reject / edit members

## Candidate group G037
- Confidence: high
- Evidence: REMARKS on 08056222: ลูกค้าสั่ง 1 ลูกค่ะ ใช้รหัสนี้แทนได้คะ (08055684)
- Members:
  - 08055684 — กระบอกเบรคหลัง 11/16 (HQ QTYMIN=0, HQ QTYOH2=1, SYP QTYOH2=0)
  - 08056222 — กระบอกเบรคหลังซ้าย 11/16 (HQ QTYMIN=-1, HQ QTYOH2=0, SYP QTYOH2=0)
- Notes: From ICMAS.REMARKS strong peer phrasing (HQ mirror).
- Reviewer action: approve / reject / edit members

## Candidate group G045
- Confidence: high
- Evidence: REMARKS on 12050286: เคยขายให้สหกิจ 18200.- ช.อ๊อด ใช้ 12050300 แทน
- Members:
  - 12050286 — วาวมือโยก 4 แกน (HQ QTYMIN=-1, HQ QTYOH2=0, SYP QTYOH2=0)
  - 12050300 — วาวมือโยก 4 แกน 4P80 (HQ QTYMIN=-1, HQ QTYOH2=0, SYP QTYOH2=0)
- Notes: From ICMAS.REMARKS strong peer phrasing (HQ mirror).
- Reviewer action: approve / reject / edit members

## Candidate group G046
- Confidence: high
- Evidence: REMARKS on 12050854: แทน (12050635)
- Members:
  - 12050635 — แหวนรองเฟืองทดหลัง ตัวใหญ่ (HQ QTYMIN=4, HQ QTYOH2=6, SYP QTYOH2=0)
  - 12050854 — แหวนรองเฟืองทด ใหญ่ (ล้อหลัง) (HQ QTYMIN=-1, HQ QTYOH2=0, SYP QTYOH2=0)
- Notes: From ICMAS.REMARKS strong peer phrasing (HQ mirror).
- Reviewer action: approve / reject / edit members

## Candidate group G047
- Confidence: high
- Evidence: REMARKS on 12051140: ใช้รหัส 12054195แทนครับ
- Members:
  - 12051140 — สปริงบายพาสวาว (HQ QTYMIN=-1, HQ QTYOH2=1, SYP QTYOH2=0)
  - 12054195 — สปริงบายพาสวาว (HQ QTYMIN=0, HQ QTYOH2=1, SYP QTYOH2=0)
- Notes: From ICMAS.REMARKS strong peer phrasing (HQ mirror).
- Reviewer action: approve / reject / edit members

## Candidate group G050
- Confidence: high
- Evidence: REMARKS on 12053270: ใช้รหัส 12052162 แทน และ ใช้ตัว4.5L 15F-5-14 ได้
- Members:
  - 12052162 — ปั้มไฮโดรลิค TD95 (HQ QTYMIN=1, HQ QTYOH2=2, SYP QTYOH2=0)
  - 12053270 — ปั้มพวงมาลัย TD95 (HQ QTYMIN=-1, HQ QTYOH2=0, SYP QTYOH2=0)
- Notes: From ICMAS.REMARKS strong peer phrasing (HQ mirror).
- Reviewer action: approve / reject / edit members

## Candidate group G051
- Confidence: high
- Evidence: REMARKS on 12052171: 12052574 ใช้รหัสนี้แทนได้
- Members:
  - 12052171 — จานไถพรวน 24" (HQ QTYMIN=-1, HQ QTYOH2=0, SYP QTYOH2=0)
  - 12052574 — จานไถพรวน 24" (HQ QTYMIN=-1, HQ QTYOH2=0, SYP QTYOH2=0)
- Notes: From ICMAS.REMARKS strong peer phrasing (HQ mirror).
- Reviewer action: approve / reject / edit members

## Candidate group G052
- Confidence: high
- Evidence: REMARKS on 12052757: 12052173 ใช้รหัสนี้แทนได้ รู53ใช้กับ55ได้
- Members:
  - 12052173 — จานไถพรวน 24" (HQ QTYMIN=4, HQ QTYOH2=42, SYP QTYOH2=0)
  - 12052757 — จานไถพรวน 24" (HQ QTYMIN=-1, HQ QTYOH2=0, SYP QTYOH2=0)
- Notes: From ICMAS.REMARKS strong peer phrasing (HQ mirror).
- Reviewer action: approve / reject / edit members

## Candidate group G056
- Confidence: high
- Evidence: REMARKS on 12053059: ราคาใหม่ 3900.- ใช้แทน 12053009
- Members:
  - 12053009 — เก้าอี้พับแขน ดำ (ที่เท้าแขนแยก) (HQ QTYMIN=2, HQ QTYOH2=6, SYP QTYOH2=0)
  - 12053059 — เก้าอี้พับแขน ดำ (ระบบโช๊ดสปริงคู่) (HQ QTYMIN=-1, HQ QTYOH2=0, SYP QTYOH2=0)
- Notes: From ICMAS.REMARKS strong peer phrasing (HQ mirror).
- Reviewer action: approve / reject / edit members

## Candidate group G063
- Confidence: high
- Evidence: REMARKS on 12054174: ใช้รหัส33010527แทน
- Members:
  - 12054174 — ข้อต่อวาวคอนโทรล (HQ QTYMIN=-1, HQ QTYOH2=16, SYP QTYOH2=?)
  - 33010527 — ข้อต่อกลาง เซาะร่องโอริง (HQ QTYMIN=4, HQ QTYOH2=9, SYP QTYOH2=0)
- Notes: From ICMAS.REMARKS strong peer phrasing (HQ mirror).
- Reviewer action: approve / reject / edit members

## Candidate group G071
- Confidence: high
- Evidence: REMARKS on 13026933: ใช้รหัส 13026955 แทน
- Members:
  - 13026933 — สปริงคันเร่ง (HQ QTYMIN=-1, HQ QTYOH2=0, SYP QTYOH2=0)
  - 13026955 — สปริงคันเร่ง (HQ QTYMIN=2, HQ QTYOH2=27, SYP QTYOH2=0)
- Notes: From ICMAS.REMARKS strong peer phrasing (HQ mirror).
- Reviewer action: approve / reject / edit members

## Candidate group G077
- Confidence: high
- Evidence: REMARKS on 13052543: หน้ากว้าง 7 นิ้ว,F334PR 7.00-12.ใช้รหัส13052672แทนตรงรุ่น
- Members:
  - 13052543 — ยางนอกล้อหน้า ขอบ12" ก้างปลา (HQ QTYMIN=-1, HQ QTYOH2=0, SYP QTYOH2=0)
  - 13052672 — ยางนอกล้อหน้า ขอบ12" ก้างปลา (HQ QTYMIN=1, HQ QTYOH2=2, SYP QTYOH2=?)
- Notes: From ICMAS.REMARKS strong peer phrasing (HQ mirror).
- Reviewer action: approve / reject / edit members

## Candidate group G080
- Confidence: high
- Evidence: REMARKS on 15020052: ใช้รหัส 15010557แทน
- Members:
  - 15010557 — ลูกปืนเข็มรูเกียร์ 3 (HQ QTYMIN=-1, HQ QTYOH2=0, SYP QTYOH2=0)
  - 15020052 — ลูกปืนปลายเดือยหมู 35-80 หลุด (HQ QTYMIN=-1, HQ QTYOH2=1, SYP QTYOH2=0)
- Notes: From ICMAS.REMARKS strong peer phrasing (HQ mirror).
- Reviewer action: approve / reject / edit members

## Candidate group G086
- Confidence: high
- Evidence: REMARKS on 16052535: ใช้รหัส 16052926 แทน
- Members:
  - 16052535 — ลูกหมากกันโครงหน้า (HQ QTYMIN=-1, HQ QTYOH2=1, SYP QTYOH2=0)
  - 16052926 — ลูกหมากกันโครงหน้า (HQ QTYMIN=0, HQ QTYOH2=5, SYP QTYOH2=?)
- Notes: From ICMAS.REMARKS strong peer phrasing (HQ mirror).
- Reviewer action: approve / reject / edit members

## Candidate group G092
- Confidence: high
- Evidence: REMARKS on 30010252: ศูนย์ 21,000.- ใช้รหัส 30010283 แทน
- Members:
  - 30010252 — ฝาสูบ 4 สูบ รุ่น  DI (HQ QTYMIN=0, HQ QTYOH2=0, SYP QTYOH2=0)
  - 30010283 — ฝาสูบแท้ 4สูบ รุ่น DI (HQ QTYMIN=-1, HQ QTYOH2=0, SYP QTYOH2=0)
- Notes: From ICMAS.REMARKS strong peer phrasing (HQ mirror).
- Reviewer action: approve / reject / edit members

## Candidate group G093
- Confidence: high
- Evidence: REMARKS on 30010261: ศูนย์1980.-   ใช้รหัสแทน 30010310
- Members:
  - 30010261 — หัวฉีดน้ำมันเชื้อเพลิง (HQ QTYMIN=-1, HQ QTYOH2=0, SYP QTYOH2=0)
  - 30010310 — หัวฉีดน้ำมันเชื้อเพลิง (HQ QTYMIN=-1, HQ QTYOH2=0, SYP QTYOH2=0)
- Notes: From ICMAS.REMARKS strong peer phrasing (HQ mirror).
- Reviewer action: approve / reject / edit members

## Candidate group G094
- Confidence: high
- Evidence: REMARKS on 30051891: ใช้รหัสแทน  30010396
- Members:
  - 30010396 — กะทะล้อหน้า 6 รู คูโบต้า ขอบ 16" (HQ QTYMIN=1, HQ QTYOH2=3, SYP QTYOH2=0)
  - 30051891 — กะทะล้อหน้า คูโบต้า ขอบ16" 4WD (HQ QTYMIN=-1, HQ QTYOH2=0, SYP QTYOH2=0)
- Notes: From ICMAS.REMARKS strong peer phrasing (HQ mirror).
- Reviewer action: approve / reject / edit members

## Candidate group G108
- Confidence: high
- Evidence: REMARKS on 30050867: 67-160/182-279/288/ของหมด ใช้กับรหัส32010035แทน
- Members:
  - 30050867 — ไส้กรองอากาศ (HQ QTYMIN=-1, HQ QTYOH2=0, SYP QTYOH2=0)
  - 32010035 — ไส้กรองอากาศ นอก+ใน มีใบพัด (HQ QTYMIN=0, HQ QTYOH2=1, SYP QTYOH2=0)
- Notes: From ICMAS.REMARKS strong peer phrasing (HQ mirror).
- Reviewer action: approve / reject / edit members

## Candidate group G110
- Confidence: high
- Evidence: REMARKS on 30051208: ใช้ 30052991 แทน
- Members:
  - 30051208 — ปะเก็นเครื่อง ชุดล่าง (HQ QTYMIN=-1, HQ QTYOH2=1, SYP QTYOH2=0)
  - 30052991 — ปะเก็นเครื่อง ชุดล่าง (HQ QTYMIN=0, HQ QTYOH2=1, SYP QTYOH2=?)
- Notes: From ICMAS.REMARKS strong peer phrasing (HQ mirror).
- Reviewer action: approve / reject / edit members

## Candidate group G114
- Confidence: high
- Evidence: REMARKS on 30051831: ใช้รหัสแทน 30052493
- Members:
  - 30051831 — สลักเฟืองทดล้อหน้า (HQ QTYMIN=-1, HQ QTYOH2=0, SYP QTYOH2=0)
  - 30052493 — สลักเฟืองทดล้อหน้า (HQ QTYMIN=3, HQ QTYOH2=1, SYP QTYOH2=0)
- Notes: From ICMAS.REMARKS strong peer phrasing (HQ mirror).
- Reviewer action: approve / reject / edit members

## Candidate group G115
- Confidence: high
- Evidence: REMARKS on 30052247: ศูนย์ขาย 660.- /ใช้รหัส 30051966 แทนค่ะ
- Members:
  - 30051966 — ชุดแขนเลื่อนเกียร์ (HQ QTYMIN=0, HQ QTYOH2=1, SYP QTYOH2=0)
  - 30052247 — ชุดแขนเลื่อนเกียร์ (HQ QTYMIN=-1, HQ QTYOH2=1, SYP QTYOH2=0)
- Notes: From ICMAS.REMARKS strong peer phrasing (HQ mirror).
- Reviewer action: approve / reject / edit members

## Candidate group G116
- Confidence: high
- Evidence: REMARKS on 30052029: SKKS750.- SMF600.- M5000 ใช้ รห้ส 30052335 แทน
- Members:
  - 30052029 — จานคลัช 11"x14T ผ้าทองแดง (HQ QTYMIN=-1, HQ QTYOH2=0, SYP QTYOH2=0)
  - 30052335 — จานคลัช 11"x14T (HQ QTYMIN=1, HQ QTYOH2=3, SYP QTYOH2=0)
- Notes: From ICMAS.REMARKS strong peer phrasing (HQ mirror).
- Reviewer action: approve / reject / edit members

## Candidate group G119
- Confidence: high
- Evidence: REMARKS on 30052108: 1G750-03312 ใช้แทนรหัส 30052459  L3608,L4018
- Members:
  - 30052108 — ปะเก็นฝาสูบเหล็ก L3608,L4018 (HQ QTYMIN=2, HQ QTYOH2=5, SYP QTYOH2=0)
  - 30052459 — ปะเก็นฝาสูบ (HQ QTYMIN=-1, HQ QTYOH2=0, SYP QTYOH2=0)
- Notes: From ICMAS.REMARKS strong peer phrasing (HQ mirror).
- Reviewer action: approve / reject / edit members

## Candidate group G121
- Confidence: high
- Evidence: REMARKS on 31050282: หมด ใช้รหัส 31050277 หรือ 31050502 แทนได้ค่ะ
- Members:
  - 31050277 — ยางกันฝุ่นเกียร์สโล/ยางกันฝุ่นเกียร์ (HQ QTYMIN=1, HQ QTYOH2=2, SYP QTYOH2=0)
  - 31050282 — ยางกันฝุ่นเกียร์ (HQ QTYMIN=-1, HQ QTYOH2=0, SYP QTYOH2=0)
- Notes: From ICMAS.REMARKS strong peer phrasing (HQ mirror).
- Reviewer action: approve / reject / edit members

## Candidate group G123
- Confidence: high
- Evidence: REMARKS on 31050941: KTC 1,800.-/ST หมด ใช้รหัส 31050884 แทน
- Members:
  - 31050884 — จานคลัช 12"x21Tx29mm (HQ QTYMIN=-1, HQ QTYOH2=0, SYP QTYOH2=0)
  - 31050941 — จานคลัช 12"x21Tx29mm (HQ QTYMIN=-1, HQ QTYOH2=0, SYP QTYOH2=0)
- Notes: From ICMAS.REMARKS strong peer phrasing (HQ mirror).
- Reviewer action: approve / reject / edit members

## Candidate group G130
- Confidence: high
- Evidence: REMARKS on 35010551: ใช้รหัสนี้แทน35010423
- Members:
  - 35010423 — ชุดแกน+จานเดือยหมูหน้า (HQ QTYMIN=1, HQ QTYOH2=2, SYP QTYOH2=0)
  - 35010551 — ชุดแกน+จานเดือยหมูหน้า (HQ QTYMIN=-1, HQ QTYOH2=0, SYP QTYOH2=0)
- Notes: From ICMAS.REMARKS strong peer phrasing (HQ mirror).
- Reviewer action: approve / reject / edit members

## Candidate group G131
- Confidence: high
- Evidence: REMARKS on 35050088: ใช้แทน 35050179
- Members:
  - 35050088 — ปะเก็นฝาสูบ (HQ QTYMIN=-1, HQ QTYOH2=0, SYP QTYOH2=0)
  - 35050179 — ปะเก็นฝาสูบ 88 มิล (HQ QTYMIN=1, HQ QTYOH2=2, SYP QTYOH2=0)
- Notes: From ICMAS.REMARKS strong peer phrasing (HQ mirror).
- Reviewer action: approve / reject / edit members

## Candidate group G132
- Confidence: high
- Evidence: REMARKS on 35050092: ยางครอบคันเกียร์ ใช้รหัส35050347แทน
- Members:
  - 35050092 — ซีล/ยางกันฝุ่นเบรค (HQ QTYMIN=-1, HQ QTYOH2=3, SYP QTYOH2=0)
  - 35050347 — ยางครอบคันเกียร์ ตัวใน (HQ QTYMIN=1, HQ QTYOH2=4, SYP QTYOH2=?)
- Notes: From ICMAS.REMARKS strong peer phrasing (HQ mirror).
- Reviewer action: approve / reject / edit members

## Candidate group G133
- Confidence: high
- Evidence: REMARKS on 35050142: CRRK 450.-/BK 500.- หมด ใช้รหัส 35050301 แทน
- Members:
  - 35050142 — แหวนลูกสูบ 92 มิล (HQ QTYMIN=-1, HQ QTYOH2=0, SYP QTYOH2=0)
  - 35050301 — แหวนลูกสูบ 92 มิล (HQ QTYMIN=2, HQ QTYOH2=4, SYP QTYOH2=0)
- Notes: From ICMAS.REMARKS strong peer phrasing (HQ mirror).
- Reviewer action: approve / reject / edit members

## Candidate group G003
- Confidence: med
- Evidence: REMARKS on 32050058: ใช้ PC200รหัส 32050152 แทนได้
- Evidence: REMARKS on 32050152: ใช้ SK200 รหัส 32050058 แทนได้
- Evidence: REMARKS on 32050396: ใช้ PC200รหัส 32050152 แทนได้
- Evidence: REMARKS on 32050410: ใช้ PC200รหัส 32050152 แทนได้
- Members:
  - 32050058 — โรลเลอร์ (HQ QTYMIN=3, HQ QTYOH2=6, SYP QTYOH2=2)
  - 32050152 — โรลเลอร์ (HQ QTYMIN=1, HQ QTYOH2=6, SYP QTYOH2=0)
  - 32050396 —  (HQ QTYMIN=0, HQ QTYOH2=?, SYP QTYOH2=?)
  - 32050410 — โรลเลอร์ (HQ QTYMIN=2, HQ QTYOH2=7, SYP QTYOH2=?)
- Notes: From ICMAS.REMARKS strong peer phrasing (HQ mirror).
- Reviewer action: approve / reject / edit members

## Candidate group G014
- Confidence: high
- Evidence: REMARKS on 02011258: ราคา3ขายช่างเท่านั้น PACO 800.-12/63 52100-3062000 ใช้รหัส02011287แทน
- Members:
  - 02011258 — คอยล์เย็น DEGA (HQ QTYMIN=0, HQ QTYOH2=1, SYP QTYOH2=1)
  - 02011287 — คอยล์เย็น DEGA (HQ QTYMIN=0, HQ QTYOH2=?, SYP QTYOH2=?)
- Notes: From ICMAS.REMARKS strong peer phrasing (HQ mirror).
- Reviewer action: approve / reject / edit members

## Candidate group G024
- Confidence: high
- Evidence: REMARKS on 05020941: ใช้ตัวนี้แทน 05010871
- Members:
  - 05010871 — ลูกหมากคันชัก สั้น นอก (HQ QTYMIN=1, HQ QTYOH2=4, SYP QTYOH2=2)
  - 05020941 — ลูกหมากคันชัก สั้น (HQ QTYMIN=1, HQ QTYOH2=2, SYP QTYOH2=0)
- Notes: From ICMAS.REMARKS strong peer phrasing (HQ mirror).
- Reviewer action: approve / reject / edit members

## Candidate group G028
- Confidence: high
- Evidence: REMARKS on 07011224: ใช่รหัส07011364แทน
- Members:
  - 07011224 — คอมแอร์ (HQ QTYMIN=0, HQ QTYOH2=0, SYP QTYOH2=0)
  - 07011364 — คอมแอร์ (HQ QTYMIN=0, HQ QTYOH2=1, SYP QTYOH2=1)
- Notes: From ICMAS.REMARKS strong peer phrasing (HQ mirror).
- Reviewer action: approve / reject / edit members

## Candidate group G059
- Confidence: high
- Evidence: REMARKS on 12053312: เกลี่ยวไม่ดี ใช้ 33010545 แทน
- Members:
  - 12053312 — ข้อต่อวาวคอนโทรล (HQ QTYMIN=2, HQ QTYOH2=0, SYP QTYOH2=0)
  - 33010545 — ข้อต่อกลาง (HQ QTYMIN=2, HQ QTYOH2=0, SYP QTYOH2=6)
- Notes: From ICMAS.REMARKS strong peer phrasing (HQ mirror).
- Reviewer action: approve / reject / edit members

## Candidate group G082
- Confidence: high
- Evidence: REMARKS on 15012213: PK 240.- TK45-4E /ใช้30050719แทนได้
- Members:
  - 15012213 — ลูกปืนคลัช 45x74x19mนูน (HQ QTYMIN=1, HQ QTYOH2=2, SYP QTYOH2=1)
  - 30050719 — ลูกปืนคลัช EF453T (HQ QTYMIN=2, HQ QTYOH2=6, SYP QTYOH2=6)
- Notes: From ICMAS.REMARKS strong peer phrasing (HQ mirror).
- Reviewer action: approve / reject / edit members

## Candidate group G096
- Confidence: high
- Evidence: REMARKS on 30050205: 33750-43532    ใช้รหัสนี้แทนได้ 30050158
- Members:
  - 30050158 — ซีลล้อหน้า-หลัง MU4902 (HQ QTYMIN=1, HQ QTYOH2=0, SYP QTYOH2=6)
  - 30050205 — ซีลล้อหลังคูโบต้า MU4902 (HQ QTYMIN=2, HQ QTYOH2=3, SYP QTYOH2=2)
- Notes: From ICMAS.REMARKS strong peer phrasing (HQ mirror).
- Reviewer action: approve / reject / edit members

## Candidate group G099
- Confidence: high
- Evidence: REMARKS on 30050216: ใช้ 30053032 แทน 20แถม2 ราคาทุนไม่หักแถม 1,400.-
- Members:
  - 30050216 — เก้าอี้รถเกี่ยวคูโบต้า รุ่น L, รุ่น M (HQ QTYMIN=4, HQ QTYOH2=15, SYP QTYOH2=1)
  - 30053032 — เก้าอี้ คูโบต้า รุ่น L, รุ่น M (HQ QTYMIN=6, HQ QTYOH2=14, SYP QTYOH2=?)
- Notes: From ICMAS.REMARKS strong peer phrasing (HQ mirror).
- Reviewer action: approve / reject / edit members

## Candidate group G102
- Confidence: high
- Evidence: REMARKS on 30050555: ใช้รหัส30052345แทน
- Members:
  - 30050555 — ชุดยางกระบอกไฮฯ KBT (HQ QTYMIN=0, HQ QTYOH2=0, SYP QTYOH2=0)
  - 30052345 — ชุดยางกระบอกไฮฯ KBT (HQ QTYMIN=1, HQ QTYOH2=2, SYP QTYOH2=1)
- Notes: From ICMAS.REMARKS strong peer phrasing (HQ mirror).
- Reviewer action: approve / reject / edit members

## Candidate group G104
- Confidence: high
- Evidence: REMARKS on 30051211: ใช้รัสแทน 30050604
- Members:
  - 30050604 — วาวไอดี KBT (HQ QTYMIN=2, HQ QTYOH2=5, SYP QTYOH2=3)
  - 30051211 — วาวไอดี KBT (หัวโต37.5xยาว101.5) (HQ QTYMIN=3, HQ QTYOH2=6, SYP QTYOH2=0)
- Notes: From ICMAS.REMARKS strong peer phrasing (HQ mirror).
- Reviewer action: approve / reject / edit members

## Candidate group G107
- Confidence: high
- Evidence: REMARKS on 30051632: 3C095-43780    ใช้แทน 30050833  M8540,M9540
- Members:
  - 30050833 — ซีลล้อหน้า (HQ QTYMIN=5, HQ QTYOH2=17, SYP QTYOH2=2)
  - 30051632 — ซีลล้อหน้า (HQ QTYMIN=2, HQ QTYOH2=5, SYP QTYOH2=2)
- Notes: From ICMAS.REMARKS strong peer phrasing (HQ mirror).
- Reviewer action: approve / reject / edit members

## Candidate group G118
- Confidence: high
- Evidence: REMARKS on 30052106: ใช้แทน 30052107
- Evidence: REMARKS on 30052107: ของหมด ใช้รหัส 30052106 แทน
- Members:
  - 30052106 — ปะเก็นฝาสูบเหล็ก หนา1.3มิล (HQ QTYMIN=1, HQ QTYOH2=3, SYP QTYOH2=0)
  - 30052107 — ปะเก็นฝาสูบเหล็ก หนา1.35มิล (HQ QTYMIN=2, HQ QTYOH2=0, SYP QTYOH2=1)
- Notes: From ICMAS.REMARKS strong peer phrasing (HQ mirror).
- Reviewer action: approve / reject / edit members

## Candidate group G122
- Confidence: high
- Evidence: REMARKS on 31050867: ใช้รหัส 31050984 นี้แทนครับ
- Members:
  - 31050867 — ไส้กรองไฮ (เหล็ก) ก1.5 (HQ QTYMIN=1, HQ QTYOH2=0, SYP QTYOH2=0)
  - 31050984 — ไส้กรองไฮ (เหล็ก) ก1.5 (HQ QTYMIN=1, HQ QTYOH2=2, SYP QTYOH2=1)
- Notes: From ICMAS.REMARKS strong peer phrasing (HQ mirror).
- Reviewer action: approve / reject / edit members

## Candidate group G023
- Confidence: high
- Evidence: REMARKS on 04050695: หมด ใช้รหัส 04050497 แทน (ต่างกันตรงขนาดปั้ม)
- Members:
  - 04050497 — ไดชาร์ท 24V 35A (ปั้มใหญ่) (HQ QTYMIN=0, HQ QTYOH2=1, SYP QTYOH2=0)
  - 04050695 — ไดชาร์ท 24V (ปั้มเล็ก) (HQ QTYMIN=0, HQ QTYOH2=0, SYP QTYOH2=0)
- Notes: From ICMAS.REMARKS strong peer phrasing (HQ mirror).
- Reviewer action: approve / reject / edit members

## Candidate group G068
- Confidence: high
- Evidence: REMARKS on 13012786: ใช้ 13018297 แทน
- Members:
  - 13012786 — ไฟสปอตไลท์ LED (HQ QTYMIN=1, HQ QTYOH2=2, SYP QTYOH2=0)
  - 13018297 — ไฟสปอร์ตไลท์ กลม 3" (HQ QTYMIN=3, HQ QTYOH2=4, SYP QTYOH2=0)
- Notes: From ICMAS.REMARKS strong peer phrasing (HQ mirror).
- Reviewer action: approve / reject / edit members

## Candidate group G134
- Confidence: med
- Evidence: same PCODE=1096253500 (6 distinct BCODEs); at least one HQ QTYMIN<0
- Members:
  - 02010676 — ซีลล้อหลังใน (HQ QTYMIN=-1, HQ QTYOH2=0, SYP QTYOH2=0)
  - 02015580 — ซีลล้อหลัง ใน (HQ QTYMIN=1, HQ QTYOH2=3, SYP QTYOH2=1)
  - 02020020 — ซีลล้อหลัง ใน (HQ QTYMIN=-1, HQ QTYOH2=0, SYP QTYOH2=0)
  - 02050190 — ซีลล้อหลังใน    แพง (HQ QTYMIN=-1, HQ QTYOH2=0, SYP QTYOH2=0)
  - 02050279 — ซีลล้อหลังใน (HQ QTYMIN=-1, HQ QTYOH2=0, SYP QTYOH2=0)
  - 80010327 — SEAL OIL (HQ QTYMIN=-1, HQ QTYOH2=0, SYP QTYOH2=0)
- Notes: PCODE twin/cluster — confirm not packaging variants before approve.
- Reviewer action: approve / reject / edit members

## Candidate group G135
- Confidence: med
- Evidence: same PCODE=111152190 (6 distinct BCODEs); at least one HQ QTYMIN<0
- Members:
  - 09011433 — ปะเก็นฝาสูบ (HQ QTYMIN=-1, HQ QTYOH2=0, SYP QTYOH2=0)
  - 09016500 — ปะเก็นฝาสูบ (HQ QTYMIN=-1, HQ QTYOH2=0, SYP QTYOH2=0)
  - 09016501 — ปะเก็นฝาสูบเหล็ก 124-2m (HQ QTYMIN=-1, HQ QTYOH2=0, SYP QTYOH2=0)
  - 09021670 — ปะเก็นฝาสูบ (HQ QTYMIN=-1, HQ QTYOH2=0, SYP QTYOH2=0)
  - 09051853 — ปะเก็นฝาสูบ เหล็ก124-2m (HQ QTYMIN=-1, HQ QTYOH2=0, SYP QTYOH2=0)
  - 09054540 — ปะเก็นฝาสูบ 2m (HQ QTYMIN=-1, HQ QTYOH2=0, SYP QTYOH2=0)
- Notes: PCODE twin/cluster — confirm not packaging variants before approve.
- Reviewer action: approve / reject / edit members

## Candidate group G136
- Confidence: med
- Evidence: same PCODE=12.4-24" (6 distinct BCODEs); at least one HQ QTYMIN<0
- Members:
  - 12010437 — ยางนอกล้อหน้า ขอบ24" ก้างปลา14บั้ง (HQ QTYMIN=-1, HQ QTYOH2=0, SYP QTYOH2=0)
  - 12010448 — ยางนอกล้อหน้า ขอบ24"ก้างปลา15บั้ง (HQ QTYMIN=2, HQ QTYOH2=4, SYP QTYOH2=0)
  - 12010549 — ยางนอกล้อหน้า ขอบ24" ก้างปลา14บั้ง (HQ QTYMIN=1, HQ QTYOH2=2, SYP QTYOH2=0)
  - 12010734 — ยางนอกล้อหน้า ขอบ24" ก้างปลา14บั้ง (HQ QTYMIN=-1, HQ QTYOH2=0, SYP QTYOH2=0)
  - 30010204 — ยางนอกล้อหลัง ขอบ24" ก้างปลา (HQ QTYMIN=-1, HQ QTYOH2=0, SYP QTYOH2=0)
  - 30010479 — ยางนอกล้อหลัง ขอบ24" ก้างปลา (HQ QTYMIN=1, HQ QTYOH2=2, SYP QTYOH2=0)
- Notes: PCODE twin/cluster — confirm not packaging variants before approve.
- Reviewer action: approve / reject / edit members

## Candidate group G137
- Confidence: med
- Evidence: same PCODE=32215 (6 distinct BCODEs); at least one HQ QTYMIN<0
- Members:
  - 15010200 — ลูกปืนล้อหลัง นอก (HQ QTYMIN=-1, HQ QTYOH2=0, SYP QTYOH2=0)
  - 15050311 — ลูกปืน (HQ QTYMIN=-1, HQ QTYOH2=0, SYP QTYOH2=0)
  - 15050425 — ลูกปืน (HQ QTYMIN=-1, HQ QTYOH2=0, SYP QTYOH2=0)
  - 15050673 — ลูกปืน (HQ QTYMIN=-1, HQ QTYOH2=0, SYP QTYOH2=0)
  - 15050745 — ลูกปืน (HQ QTYMIN=-1, HQ QTYOH2=0, SYP QTYOH2=0)
  - 15050782 — ลูกปืน (HQ QTYMIN=5, HQ QTYOH2=16, SYP QTYOH2=3)
- Notes: PCODE twin/cluster — confirm not packaging variants before approve.
- Reviewer action: approve / reject / edit members

## Candidate group G138
- Confidence: med
- Evidence: same PCODE=4331009015 (6 distinct BCODEs); at least one HQ QTYMIN<0
- Members:
  - 08011547 — ลูกหมากปีกนกบน (HQ QTYMIN=-1, HQ QTYOH2=0, SYP QTYOH2=0)
  - 08051808 — ลูกหมากปีกนกบน (HQ QTYMIN=-1, HQ QTYOH2=0, SYP QTYOH2=0)
  - 08054523 — ลูกหมากปีกนกบน (HQ QTYMIN=2, HQ QTYOH2=2, SYP QTYOH2=2)
  - 08054526 — ลูกหมากปีกนกบน (HQ QTYMIN=-1, HQ QTYOH2=0, SYP QTYOH2=0)
  - 08056510 — ลูกหมากปีกนกบน (HQ QTYMIN=2, HQ QTYOH2=2, SYP QTYOH2=2)
  - 08056772 — ลูกหมากปีกนกบน (HQ QTYMIN=2, HQ QTYOH2=4, SYP QTYOH2=?)
- Notes: PCODE twin/cluster — confirm not packaging variants before approve.
- Reviewer action: approve / reject / edit members

## Candidate group G139
- Confidence: med
- Evidence: same PCODE=6-8cm (6 distinct BCODEs); at least one HQ QTYMIN<0
- Members:
  - 13010832 — หม้อลมเบรคติดปั้ม 1.5ชั้น (HQ QTYMIN=-1, HQ QTYOH2=0, SYP QTYOH2=0)
  - 13011971 — หม้อลมเบรค+แม้ปั้ม 1.5 ตอน (HQ QTYMIN=-1, HQ QTYOH2=0, SYP QTYOH2=0)
  - 13015221 — หม้อลมเบรค+แม่ปั้ม1.5ตอน (HQ QTYMIN=-1, HQ QTYOH2=0, SYP QTYOH2=0)
  - 13034311 — หม้อลมเบรค+แม่ปั้ม6-8cm. (HQ QTYMIN=-1, HQ QTYOH2=0, SYP QTYOH2=0)
  - 13034313 — หม้อลมเบรค1.5ตอน (HQ QTYMIN=-1, HQ QTYOH2=0, SYP QTYOH2=0)
  - 13034315 — หม้อลมเบรค+แม่ปั้ม1.5ตอน (HQ QTYMIN=-1, HQ QTYOH2=0, SYP QTYOH2=0)
- Notes: PCODE twin/cluster — confirm not packaging variants before approve.
- Reviewer action: approve / reject / edit members

## Candidate group G140
- Confidence: med
- Evidence: same PCODE=81874740 (6 distinct BCODEs); at least one HQ QTYMIN<0
- Members:
  - 12050611 — ยอยกากบาทเพลาหน้าคาราโร่ (HQ QTYMIN=-1, HQ QTYOH2=0, SYP QTYOH2=0)
  - 12051904 — ยอยกากบาทเพลาหน้าคาราโร่ (HQ QTYMIN=-1, HQ QTYOH2=0, SYP QTYOH2=0)
  - 12052146 — ยอยกากบาทเพลาหน้าคาราโร่ (HQ QTYMIN=2, HQ QTYOH2=0, SYP QTYOH2=0)
  - 12052331 — ยอยกากบาทเพลาหน้าคาราโร่ (HQ QTYMIN=4, HQ QTYOH2=7, SYP QTYOH2=3)
  - 12052954 — ยอยกากบาทเพลาหน้าคาราโร่ (HQ QTYMIN=2, HQ QTYOH2=11, SYP QTYOH2=2)
  - 12053712 — ยอยกากบาทเพลาหน้าคาราโร่ (HQ QTYMIN=-1, HQ QTYOH2=0, SYP QTYOH2=0)
- Notes: PCODE twin/cluster — confirm not packaging variants before approve.
- Reviewer action: approve / reject / edit members

## Candidate group G141
- Confidence: med
- Evidence: same PCODE=89973973 (6 distinct BCODEs); at least one HQ QTYMIN<0
- Members:
  - 12052166 — จานคลัช 13" ไม่มีสปริง (HQ QTYMIN=-1, HQ QTYOH2=0, SYP QTYOH2=0)
  - 12053122 — จานคลัช 13" ไม่มีสปริง (HQ QTYMIN=-1, HQ QTYOH2=0, SYP QTYOH2=0)
  - 12053285 — จานคลัช 13" 10Tx45mm. (HQ QTYMIN=1, HQ QTYOH2=5, SYP QTYOH2=1)
  - 12053384 — จานคลัช 13" ไม่มีสปริง (HQ QTYMIN=-1, HQ QTYOH2=0, SYP QTYOH2=0)
  - 12053977 — จานคลัช 13" ไม่มีสปริง (HQ QTYMIN=-1, HQ QTYOH2=0, SYP QTYOH2=?)
  - 12054175 — จานคลัช 13" 10Tx45mm. (HQ QTYMIN=2, HQ QTYOH2=?, SYP QTYOH2=?)
- Notes: PCODE twin/cluster — confirm not packaging variants before approve.
- Reviewer action: approve / reject / edit members

## Candidate group G142
- Confidence: med
- Evidence: same PCODE=ALMERA (6 distinct BCODEs); at least one HQ QTYMIN<0
- Members:
  - 29011138 — ฝาครอบไฟท้าย ชุบ (HQ QTYMIN=-1, HQ QTYOH2=0, SYP QTYOH2=0)
  - 29011140 — กันสาดประตู (HQ QTYMIN=-1, HQ QTYOH2=0, SYP QTYOH2=0)
  - 29011596 — ครอบฝาถังน้ำมัน ชุบขอบหยัก (HQ QTYMIN=-1, HQ QTYOH2=0, SYP QTYOH2=0)
  - 29011599 — ฝาครอบไฟหน้า ชุบ (HQ QTYMIN=-1, HQ QTYOH2=0, SYP QTYOH2=0)
  - 29011600 — ฝาครอบมือเปิดฝาท้าย (HQ QTYMIN=-1, HQ QTYOH2=0, SYP QTYOH2=0)
  - 29011743 — ครอบฝาถังน้ำมัน ชุบ (HQ QTYMIN=-1, HQ QTYOH2=0, SYP QTYOH2=0)
- Notes: PCODE twin/cluster — confirm not packaging variants before approve.
- Reviewer action: approve / reject / edit members

## Candidate group G143
- Confidence: med
- Evidence: same PCODE=C5NN4969E (6 distinct BCODEs); at least one HQ QTYMIN<0
- Members:
  - 12050849 — ซีลล้อหลัง O'SIZE (HQ QTYMIN=4, HQ QTYOH2=9, SYP QTYOH2=2)
  - 12051517 — ซีลล้อหลัง ขอบยาง (HQ QTYMIN=-1, HQ QTYOH2=0, SYP QTYOH2=0)
  - 12052102 — ซีลล้อหลัง เดิม (HQ QTYMIN=-1, HQ QTYOH2=0, SYP QTYOH2=0)
  - 12053217 — ซีลล้อหลัง เดิม ขอบยาง (HQ QTYMIN=-1, HQ QTYOH2=0, SYP QTYOH2=0)
  - 12053726 — ซีลล้อหลัง เดิม ขอบยาง (HQ QTYMIN=-1, HQ QTYOH2=0, SYP QTYOH2=0)
  - 12053803 — ซีลล้อหลัง เดิม ขอบยาง (HQ QTYMIN=2, HQ QTYOH2=4, SYP QTYOH2=0)
- Notes: PCODE twin/cluster — confirm not packaging variants before approve.
- Reviewer action: approve / reject / edit members

## Candidate group G144
- Confidence: med
- Evidence: same PCODE=MD603800 (6 distinct BCODEs); at least one HQ QTYMIN<0
- Members:
  - 11010529 — ไส้กรองอากาศ ก. คาบิว (HQ QTYMIN=-1, HQ QTYOH2=0, SYP QTYOH2=0)
  - 11012910 — ไส้กรองอากาศ ก. คาบิว (HQ QTYMIN=-1, HQ QTYOH2=0, SYP QTYOH2=0)
  - 11015500 — ไส้กรองอากาศ ก. คาบิว (HQ QTYMIN=-1, HQ QTYOH2=0, SYP QTYOH2=0)
  - 11050432 — ไส้กรองอากาศ ก. คาบิว (HQ QTYMIN=-1, HQ QTYOH2=0, SYP QTYOH2=0)
  - 11051708 — ไส้กรองอากาศ กลม (HQ QTYMIN=-1, HQ QTYOH2=0, SYP QTYOH2=0)
  - 11052183 — ไส้กรองอากาศ กลม (HQ QTYMIN=-1, HQ QTYOH2=1, SYP QTYOH2=0)
- Notes: PCODE twin/cluster — confirm not packaging variants before approve.
- Reviewer action: approve / reject / edit members

## Candidate group G145
- Confidence: med
- Evidence: same PCODE=MR353453 (6 distinct BCODEs); at least one HQ QTYMIN<0
- Members:
  - 05010741 — แหนบหลัง หู (HQ QTYMIN=0, HQ QTYOH2=2, SYP QTYOH2=0)
  - 05010771 — แหนบหลัง (HQ QTYMIN=-1, HQ QTYOH2=2, SYP QTYOH2=0)
  - 11011494 — แหนบหลัง ตัวที่ 2 (HQ QTYMIN=1, HQ QTYOH2=3, SYP QTYOH2=0)
  - 11051914 — แหนบหลัง ทั้งตับ (HQ QTYMIN=-1, HQ QTYOH2=2, SYP QTYOH2=0)
  - 11051922 — แหนบหลัง รัด (HQ QTYMIN=-1, HQ QTYOH2=3, SYP QTYOH2=0)
  - 11051923 — แหนบหลัง หู (HQ QTYMIN=0, HQ QTYOH2=1, SYP QTYOH2=0)
- Notes: PCODE twin/cluster — confirm not packaging variants before approve.
- Reviewer action: approve / reject / edit members

## Candidate group G146
- Confidence: med
- Evidence: same PCODE=040100415 (5 distinct BCODEs); at least one HQ QTYMIN<0
- Members:
  - 09010035 — ปะเก็นชุดใหญ่ (HQ QTYMIN=-1, HQ QTYOH2=0, SYP QTYOH2=0)
  - 09010102 — ปะเก็นชุดใหญ่ ฝาTOP (HQ QTYMIN=-1, HQ QTYOH2=0, SYP QTYOH2=0)
  - 09011153 — ปะเก็นชุดใหญ่ ไม่ฝา-ไม่ซีล (HQ QTYMIN=-1, HQ QTYOH2=0, SYP QTYOH2=0)
  - 09011438 — ปะเก็นชุดใหญ่ (HQ QTYMIN=-1, HQ QTYOH2=0, SYP QTYOH2=0)
  - 80010235 — GASKET KIT ENGINE OVERHAUL (HQ QTYMIN=-1, HQ QTYOH2=0, SYP QTYOH2=0)
- Notes: PCODE twin/cluster — confirm not packaging variants before approve.
- Reviewer action: approve / reject / edit members

## Candidate group G147
- Confidence: med
- Evidence: same PCODE=042260L010 (5 distinct BCODEs); at least one HQ QTYMIN<0
- Members:
  - 08055518 — สวิทตูดปั้ม (SCV วาว) (HQ QTYMIN=-1, HQ QTYOH2=0, SYP QTYOH2=0)
  - 08055657 — สวิทตูดปั้ม SCV (HQ QTYMIN=0, HQ QTYOH2=1, SYP QTYOH2=1)
  - 08055789 — สวิทตูดปั้ม (SCV วาว) (HQ QTYMIN=-1, HQ QTYOH2=0, SYP QTYOH2=0)
  - 13010356 — สวิทตูดปั้ม 20-30ย.50m+ปลอก+รอง (HQ QTYMIN=-1, HQ QTYOH2=0, SYP QTYOH2=0)
  - 13050290 — สวิทตูดปั้ม 19-33ย.50 KDH222 (HQ QTYMIN=-1, HQ QTYOH2=0, SYP QTYOH2=0)
- Notes: PCODE twin/cluster — confirm not packaging variants before approve.
- Reviewer action: approve / reject / edit members

## Candidate group G148
- Confidence: med
- Evidence: same PCODE=042260L020 (5 distinct BCODEs); at least one HQ QTYMIN<0
- Members:
  - 08055656 — สวิทตูดปั้ม SCV (HQ QTYMIN=-1, HQ QTYOH2=0, SYP QTYOH2=0)
  - 08056691 — สวิทตูดปั้ม SCV (HQ QTYMIN=0, HQ QTYOH2=?, SYP QTYOH2=0)
  - 13050289 — สวิทตูดปั้ม 20-30ย.50 (HQ QTYMIN=-1, HQ QTYOH2=0, SYP QTYOH2=0)
  - 13050351 — สวิทตูดปั้ม 20-30ย.50m (HQ QTYMIN=-1, HQ QTYOH2=0, SYP QTYOH2=0)
  - 13050352 — สวิทตูดปั้ม 20-30ย.50m (HQ QTYMIN=-1, HQ QTYOH2=0, SYP QTYOH2=0)
- Notes: PCODE twin/cluster — confirm not packaging variants before approve.
- Reviewer action: approve / reject / edit members

## Candidate group G149
- Confidence: med
- Evidence: same PCODE=0447940010 (5 distinct BCODEs); at least one HQ QTYMIN<0
- Members:
  - 08010768 — ยางดิสเบรคหน้า (HQ QTYMIN=-1, HQ QTYOH2=0, SYP QTYOH2=0)
  - 08011085 — ยางดิสเบรคหน้า (HQ QTYMIN=-1, HQ QTYOH2=0, SYP QTYOH2=0)
  - 08011190 — ยางดิสเบรคหน้า 62m (HQ QTYMIN=-1, HQ QTYOH2=0, SYP QTYOH2=0)
  - 08014768 — ยางดิสเบรคหน้า 62m (HQ QTYMIN=2, HQ QTYOH2=4, SYP QTYOH2=2)
  - 08054686 — ยางดิสเบรคหน้า 62m (HQ QTYMIN=-1, HQ QTYOH2=0, SYP QTYOH2=0)
- Notes: PCODE twin/cluster — confirm not packaging variants before approve.
- Reviewer action: approve / reject / edit members

## Candidate group G150
- Confidence: med
- Evidence: same PCODE=1121211180 (5 distinct BCODEs); at least one HQ QTYMIN<0
- Members:
  - 02011128 — แหวนลูกสูบ* ร่องล.102m (HQ QTYMIN=-1, HQ QTYOH2=0, SYP QTYOH2=0)
  - 02017930 — แหวนลูกสูบ ร่องล.102m (HQ QTYMIN=-1, HQ QTYOH2=0, SYP QTYOH2=0)
  - 02051370 — แหวนลูกสูบร่องล.102m 2.5-3-5m (HQ QTYMIN=-1, HQ QTYOH2=0, SYP QTYOH2=0)
  - 04050480 — แหวนลูกสูบ ร่องเหล็ก 102m (HQ QTYMIN=-1, HQ QTYOH2=0, SYP QTYOH2=0)
  - 04051750 — แหวนลูกสูบ ร่องล.102m (HQ QTYMIN=-1, HQ QTYOH2=1, SYP QTYOH2=0)
- Notes: PCODE twin/cluster — confirm not packaging variants before approve.
- Reviewer action: approve / reject / edit members

## Candidate group G151
- Confidence: med
- Evidence: same PCODE=17311-22310 (5 distinct BCODEs); at least one HQ QTYMIN<0
- Members:
  - 30050595 — ชาพก้าน STD (HQ QTYMIN=-1, HQ QTYOH2=0, SYP QTYOH2=0)
  - 30051721 — ชาพก้าน 020 (HQ QTYMIN=-1, HQ QTYOH2=2, SYP QTYOH2=0)
  - 30052401 — ชาพก้าน 030 (HQ QTYMIN=2, HQ QTYOH2=6, SYP QTYOH2=0)
  - 30052402 — ชาพก้าน 040 (HQ QTYMIN=2, HQ QTYOH2=4, SYP QTYOH2=0)
  - 30052531 — ชาพก้าน STD (HQ QTYMIN=5, HQ QTYOH2=12, SYP QTYOH2=4)
- Notes: PCODE twin/cluster — confirm not packaging variants before approve.
- Reviewer action: approve / reject / edit members

## Candidate group G152
- Confidence: med
- Evidence: same PCODE=1820187G00 (5 distinct BCODEs); at least one HQ QTYMIN<0
- Members:
  - 05010843 — สายคันเร่งอย่างดี (HQ QTYMIN=1, HQ QTYOH2=2, SYP QTYOH2=1)
  - 05011748 — สายคันเร่งอย่างดี (HQ QTYMIN=-1, HQ QTYOH2=1, SYP QTYOH2=0)
  - 05011807 — สายคันเร่งอย่างดี (HQ QTYMIN=0, HQ QTYOH2=1, SYP QTYOH2=1)
  - 05017860 — สายคันเร่ง 122ซม. (HQ QTYMIN=-1, HQ QTYOH2=0, SYP QTYOH2=0)
  - 05052170 — สายคันเร่ง (HQ QTYMIN=-1, HQ QTYOH2=0, SYP QTYOH2=0)
- Notes: PCODE twin/cluster — confirm not packaging variants before approve.
- Reviewer action: approve / reject / edit members

## Candidate group G153
- Confidence: med
- Evidence: same PCODE=1868435M3 (5 distinct BCODEs); at least one HQ QTYMIN<0
- Members:
  - 31050119 — แชมเปอร์วาวไฮ (HQ QTYMIN=-1, HQ QTYOH2=0, SYP QTYOH2=0)
  - 31050221 — แชมเปอร์วาวไฮ+วาว (HQ QTYMIN=-1, HQ QTYOH2=0, SYP QTYOH2=0)
  - 31050326 — แชมเปอร์วาวไฮ+วาว (HQ QTYMIN=-1, HQ QTYOH2=0, SYP QTYOH2=0)
  - 31050766 — แชมเปอร์วาวไฮ (HQ QTYMIN=0, HQ QTYOH2=1, SYP QTYOH2=0)
  - 31051000 — แชมเปอร์วาวไฮ+วาว (HQ QTYMIN=1, HQ QTYOH2=0, SYP QTYOH2=?)
- Notes: PCODE twin/cluster — confirm not packaging variants before approve.
- Reviewer action: approve / reject / edit members

## Candidate group G154
- Confidence: med
- Evidence: same PCODE=23390YZZA1 (5 distinct BCODEs); at least one HQ QTYMIN<0
- Members:
  - 08065953 — ไส้กรองโซล่า กระดาษ (HQ QTYMIN=-1, HQ QTYOH2=0, SYP QTYOH2=0)
  - 08065955 — ไส้กรองโซล่า กระดาษ (HQ QTYMIN=-1, HQ QTYOH2=0, SYP QTYOH2=0)
  - 08065958 — ไส้กรองโซล่า กระดาษ (HQ QTYMIN=-1, HQ QTYOH2=0, SYP QTYOH2=0)
  - 08065959 — ไส้กรองโซล่า กระดาษ (HQ QTYMIN=-1, HQ QTYOH2=0, SYP QTYOH2=0)
  - 08065961 — ไส้กรองโซล่า กระดาษหยาบ (HQ QTYMIN=-1, HQ QTYOH2=1, SYP QTYOH2=0)
- Notes: PCODE twin/cluster — confirm not packaging variants before approve.
- Reviewer action: approve / reject / edit members

## Candidate group G155
- Confidence: med
- Evidence: same PCODE=27415-0L030 (5 distinct BCODEs); at least one HQ QTYMIN<0
- Members:
  - 08012317 — มูเล่ย์ไดชาร์จ 7PK รู15 มิล (HQ QTYMIN=-1, HQ QTYOH2=1, SYP QTYOH2=1)
  - 08014843 — มูเล่ย์ไดชาร์จ 7PK รู15 มิล (HQ QTYMIN=1, HQ QTYOH2=2, SYP QTYOH2=1)
  - 08055218 — มูเล่ย์ไดชาร์จ (HQ QTYMIN=-1, HQ QTYOH2=0, SYP QTYOH2=0)
  - 08056295 — มูเล่ย์ไดชาร์จ (HQ QTYMIN=1, HQ QTYOH2=1, SYP QTYOH2=1)
  - 08057081 — มูเล่ย์ไดชาร์จ 7PK รู15 มิล (HQ QTYMIN=0, HQ QTYOH2=0, SYP QTYOH2=1)
- Notes: PCODE twin/cluster — confirm not packaging variants before approve.
- Reviewer action: approve / reject / edit members

## Candidate group G156
- Confidence: med
- Evidence: same PCODE=3133944510 (5 distinct BCODEs); at least one HQ QTYMIN<0
- Members:
  - 30050208 — ซีลล้อหลังคูโบต้า (HQ QTYMIN=-1, HQ QTYOH2=0, SYP QTYOH2=0)
  - 30050962 — ซีลล้อหลังคูโบต้า (HQ QTYMIN=-1, HQ QTYOH2=0, SYP QTYOH2=0)
  - 30051085 — ซีลล้อหลังคูโบต้า (HQ QTYMIN=4, HQ QTYOH2=10, SYP QTYOH2=2)
  - 30051115 — ซีลล้อหลังคูโบต้า (HQ QTYMIN=-1, HQ QTYOH2=0, SYP QTYOH2=0)
  - 30051229 — ซีลล้อหลังคูโบต้า (HQ QTYMIN=-1, HQ QTYOH2=0, SYP QTYOH2=0)
- Notes: PCODE twin/cluster — confirm not packaging variants before approve.
- Reviewer action: approve / reject / edit members

## Candidate group G157
- Confidence: med
- Evidence: same PCODE=3A121-43140 (5 distinct BCODEs); at least one HQ QTYMIN<0
- Members:
  - 30051015 — เฟืองดอกจอกหน้าใหญ่ตัวสั้น MU5501 (HQ QTYMIN=-1, HQ QTYOH2=0, SYP QTYOH2=0)
  - 30052445 — เฟืองดอกจอกหน้าใหญ่ตัวสั้น MU5501 (HQ QTYMIN=-1, HQ QTYOH2=0, SYP QTYOH2=0)
  - 30052484 — เฟืองดอกจอกหน้าใหญ่ตัวสั้น MU5501 (HQ QTYMIN=1, HQ QTYOH2=2, SYP QTYOH2=2)
  - 30052678 — เฟืองดอกจอกหน้าใหญ่ตัวสั้น (HQ QTYMIN=1, HQ QTYOH2=2, SYP QTYOH2=0)
  - 30052868 — เฟืองดอกจอกหน้าตัวใหญ่ 14ฟัน (HQ QTYMIN=1, HQ QTYOH2=2, SYP QTYOH2=1)
- Notes: PCODE twin/cluster — confirm not packaging variants before approve.
- Reviewer action: approve / reject / edit members

## Candidate group G158
- Confidence: med
- Evidence: same PCODE=4410008W22 (5 distinct BCODEs); at least one HQ QTYMIN<0
- Members:
  - 05011005 — กระบอกเบรคหลัง (HQ QTYMIN=-1, HQ QTYOH2=0, SYP QTYOH2=0)
  - 05011044 — กระบอกเบรคหลัง2สกรู (HQ QTYMIN=-1, HQ QTYOH2=0, SYP QTYOH2=0)
  - 05011108 — กระบอกเบรคหลัง2สกรู (HQ QTYMIN=-1, HQ QTYOH2=0, SYP QTYOH2=0)
  - 05019690 — กระบอกเบรคหลัง (HQ QTYMIN=-1, HQ QTYOH2=0, SYP QTYOH2=0)
  - 05037090 — กระบอกเบรคหลัง (HQ QTYMIN=-1, HQ QTYOH2=0, SYP QTYOH2=0)
- Notes: PCODE twin/cluster — confirm not packaging variants before approve.
- Reviewer action: approve / reject / edit members

## Candidate group G159
- Confidence: med
- Evidence: same PCODE=4550309321 (5 distinct BCODEs); at least one HQ QTYMIN<0
- Members:
  - 08054549 — ลูกหมากแร็ค 14-15m-12.2" (HQ QTYMIN=-1, HQ QTYOH2=2, SYP QTYOH2=2)
  - 08054551 — ลูกหมากแร็ค 14-15m-12.2" (HQ QTYMIN=-1, HQ QTYOH2=1, SYP QTYOH2=0)
  - 08055221 — ลูกหมากแร็ค 14-15m-12.2" (HQ QTYMIN=-1, HQ QTYOH2=0, SYP QTYOH2=0)
  - 08056459 — ลูกหมากแร็ค 14-15m-12.2" (HQ QTYMIN=1, HQ QTYOH2=4, SYP QTYOH2=2)
  - 08056773 — ลูกหมากแร็ค 14-15m-12.2" (HQ QTYMIN=2, HQ QTYOH2=6, SYP QTYOH2=4)
- Notes: PCODE twin/cluster — confirm not packaging variants before approve.
- Reviewer action: approve / reject / edit members

## Candidate group G160
- Confidence: med
- Evidence: same PCODE=4720135790 (5 distinct BCODEs); at least one HQ QTYMIN<0
- Members:
  - 08012004 — แม่ปั้มเบรค 1" (HQ QTYMIN=-1, HQ QTYOH2=0, SYP QTYOH2=0)
  - 08054747 — แม่ปั้มเบรค 1" (HQ QTYMIN=-1, HQ QTYOH2=0, SYP QTYOH2=0)
  - 08055686 — แม่ปั้มเบรค 1" (HQ QTYMIN=-1, HQ QTYOH2=0, SYP QTYOH2=0)
  - 08055719 — แม่ปั้มเบรค 1" (HQ QTYMIN=-1, HQ QTYOH2=0, SYP QTYOH2=0)
  - 08055822 — แม่ปั้มเบรค 1" (HQ QTYMIN=0, HQ QTYOH2=1, SYP QTYOH2=0)
- Notes: PCODE twin/cluster — confirm not packaging variants before approve.
- Reviewer action: approve / reject / edit members

## Candidate group G161
- Confidence: med
- Evidence: same PCODE=482010K130 (5 distinct BCODEs); at least one HQ QTYMIN<0
- Members:
  - 08053881 — แหนบหลัง+บู๊ช (HQ QTYMIN=-1, HQ QTYOH2=0, SYP QTYOH2=0)
  - 08054255 — แหนบหลัง (HQ QTYMIN=-1, HQ QTYOH2=0, SYP QTYOH2=0)
  - 08054256 — แหนบหลัง (HQ QTYMIN=-1, HQ QTYOH2=0, SYP QTYOH2=0)
  - 08054257 — แหนบหลัง (HQ QTYMIN=-1, HQ QTYOH2=0, SYP QTYOH2=0)
  - 08054258 — แหนบหลัง (HQ QTYMIN=-1, HQ QTYOH2=0, SYP QTYOH2=0)
- Notes: PCODE twin/cluster — confirm not packaging variants before approve.
- Reviewer action: approve / reject / edit members

## Candidate group G162
- Confidence: med
- Evidence: same PCODE=48210356501 (5 distinct BCODEs); at least one HQ QTYMIN<0
- Members:
  - 08025542 — แหนบหลัง (HQ QTYMIN=-1, HQ QTYOH2=0, SYP QTYOH2=0)
  - 08031961 — แหนบหลัง รัด 1 งอ (HQ QTYMIN=-1, HQ QTYOH2=0, SYP QTYOH2=0)
  - 08038080 — แหนบหลัง 20" รัด (HQ QTYMIN=0, HQ QTYOH2=3, SYP QTYOH2=0)
  - 08038090 — แหนบหลัง 34" (HQ QTYMIN=-1, HQ QTYOH2=3, SYP QTYOH2=0)
  - 08055586 — แหนบหลัง ตัวที่ 2 (HQ QTYMIN=-1, HQ QTYOH2=0, SYP QTYOH2=0)
- Notes: PCODE twin/cluster — confirm not packaging variants before approve.
- Reviewer action: approve / reject / edit members

## Candidate group G163
- Confidence: med
- Evidence: same PCODE=486540K040 (5 distinct BCODEs); at least one HQ QTYMIN<0
- Members:
  - 08014262 — บู๊ชปีกนกล่าง ตัวเล็ก (HQ QTYMIN=-1, HQ QTYOH2=0, SYP QTYOH2=0)
  - 08054541 — บู๊ชปีกนกล่าง ตัวเล็ก (HQ QTYMIN=2, HQ QTYOH2=5, SYP QTYOH2=1)
  - 08054544 — บู๊ชปีกนกล่าง ตัวเล็ก (HQ QTYMIN=-1, HQ QTYOH2=0, SYP QTYOH2=0)
  - 08055581 — บู๊ชปีกนกล่าง ตัวเล็ก (HQ QTYMIN=1, HQ QTYOH2=2, SYP QTYOH2=0)
  - 08056437 — บู๊ชปีกนกล่าง ตัวเล็ก (HQ QTYMIN=-1, HQ QTYOH2=2, SYP QTYOH2=0)
- Notes: PCODE twin/cluster — confirm not packaging variants before approve.
- Reviewer action: approve / reject / edit members

## Candidate group G164
- Confidence: med
- Evidence: same PCODE=486550K010 (5 distinct BCODEs); at least one HQ QTYMIN<0
- Members:
  - 08010938 — บู๊ชปีกนกล่าง ตัวใหญ่ (HQ QTYMIN=-1, HQ QTYOH2=0, SYP QTYOH2=0)
  - 08010941 — บู๊ชปีกนกล่าง ตัวใหญ่ (HQ QTYMIN=2, HQ QTYOH2=7, SYP QTYOH2=2)
  - 08010948 — บู๊ชปีกนกล่าง ตัวใหญ่ (HQ QTYMIN=-1, HQ QTYOH2=0, SYP QTYOH2=0)
  - 08051811 — บู๊ชปีกนกล่าง ตัวใหญ่ (HQ QTYMIN=-1, HQ QTYOH2=0, SYP QTYOH2=0)
  - 08052172 — บู๊ชปีกนกล่าง ตัวใหญ่ (HQ QTYMIN=-1, HQ QTYOH2=0, SYP QTYOH2=0)
- Notes: PCODE twin/cluster — confirm not packaging variants before approve.
- Reviewer action: approve / reject / edit members

## Candidate group G165
- Confidence: med
- Evidence: same PCODE=82012210 (5 distinct BCODEs); at least one HQ QTYMIN<0
- Members:
  - 12050718 — ฝาถังน้ำมันโซล่า (HQ QTYMIN=-1, HQ QTYOH2=0, SYP QTYOH2=0)
  - 12050719 — ฝาถังน้ำมันโซล่า ถังพลาสติก (HQ QTYMIN=-1, HQ QTYOH2=0, SYP QTYOH2=1)
  - 12052562 — ฝาถังน้ำมันโซล่า มีกุญแจ (HQ QTYMIN=1, HQ QTYOH2=1, SYP QTYOH2=1)
  - 12053253 — ฝาถังน้ำมันโซล่า (HQ QTYMIN=0, HQ QTYOH2=0, SYP QTYOH2=0)
  - 12053714 — ฝาถังน้ำมันโซล่า ถังพลาสติก (HQ QTYMIN=1, HQ QTYOH2=3, SYP QTYOH2=1)
- Notes: PCODE twin/cluster — confirm not packaging variants before approve.
- Reviewer action: approve / reject / edit members

## Candidate group G166
- Confidence: med
- Evidence: same PCODE=83909255 (5 distinct BCODEs); at least one HQ QTYMIN<0
- Members:
  - 12051141 — บายพาสวาล์ว (HQ QTYMIN=0, HQ QTYOH2=1, SYP QTYOH2=0)
  - 12051849 — บายพาสวาว (HQ QTYMIN=-1, HQ QTYOH2=1, SYP QTYOH2=0)
  - 12051850 — บายพาสวาว (HQ QTYMIN=-1, HQ QTYOH2=1, SYP QTYOH2=0)
  - 12051851 — บายพาสวาว (HQ QTYMIN=-1, HQ QTYOH2=1, SYP QTYOH2=0)
  - 12051852 — บายพาสวาว (HQ QTYMIN=-1, HQ QTYOH2=0, SYP QTYOH2=0)
- Notes: PCODE twin/cluster — confirm not packaging variants before approve.
- Reviewer action: approve / reject / edit members

## Candidate group G167
- Confidence: med
- Evidence: same PCODE=83924926 (5 distinct BCODEs); at least one HQ QTYMIN<0
- Members:
  - 12050688 — ซีลปลายเกียร์ 4 (HQ QTYMIN=-1, HQ QTYOH2=0, SYP QTYOH2=0)
  - 12051431 — ซีลปลายเกียร์ 4 (HQ QTYMIN=-1, HQ QTYOH2=0, SYP QTYOH2=0)
  - 12051709 — ซีลปลายเกียร์ 4 (HQ QTYMIN=-1, HQ QTYOH2=0, SYP QTYOH2=0)
  - 12052041 — ซีลปลายเกียร์ 4 (HQ QTYMIN=-1, HQ QTYOH2=0, SYP QTYOH2=0)
  - 12052046 — ซีลปลายเกียร์ 4  MIS25 (HQ QTYMIN=2, HQ QTYOH2=6, SYP QTYOH2=2)
- Notes: PCODE twin/cluster — confirm not packaging variants before approve.
- Reviewer action: approve / reject / edit members

## Candidate group G168
- Confidence: med
- Evidence: same PCODE=894166859 (5 distinct BCODEs); at least one HQ QTYMIN<0
- Members:
  - 03010360 — แหนบหลัง 22" (HQ QTYMIN=-1, HQ QTYOH2=5, SYP QTYOH2=0)
  - 03011110 — แหนบหลัง (HQ QTYMIN=-1, HQ QTYOH2=0, SYP QTYOH2=0)
  - 03013130 — แหนบหลัง รัด 34" (HQ QTYMIN=-1, HQ QTYOH2=3, SYP QTYOH2=0)
  - 03017110 — แหนบหลัง รัด (HQ QTYMIN=-1, HQ QTYOH2=1, SYP QTYOH2=0)
  - 07011168 — แหนบหลัง เสริมตรง (HQ QTYMIN=-1, HQ QTYOH2=2, SYP QTYOH2=0)
- Notes: PCODE twin/cluster — confirm not packaging variants before approve.
- Reviewer action: approve / reject / edit members

## Candidate group G169
- Confidence: med
- Evidence: same PCODE=8970967770 (5 distinct BCODEs); at least one HQ QTYMIN<0
- Members:
  - 04016320 — ไส้กรองเครื่อง เหล็ก ก.12NF (HQ QTYMIN=-1, HQ QTYOH2=0, SYP QTYOH2=0)
  - 04016890 — ไส้กรองเครื่อง (HQ QTYMIN=-1, HQ QTYOH2=0, SYP QTYOH2=0)
  - 04050282 — ไส้กรองเครื่อง เหล็ก ก.12NF (HQ QTYMIN=-1, HQ QTYOH2=0, SYP QTYOH2=0)
  - 04050693 — ไส้กรองเครื่อง เหล็ก ก.12NF (HQ QTYMIN=-1, HQ QTYOH2=0, SYP QTYOH2=0)
  - 04050698 — ไส้กรองเครื่อง เหล็ก ก.12NF (HQ QTYMIN=2, HQ QTYOH2=2, SYP QTYOH2=4)
- Notes: PCODE twin/cluster — confirm not packaging variants before approve.
- Reviewer action: approve / reject / edit members

## Candidate group G170
- Confidence: med
- Evidence: same PCODE=90915YZZD2 (5 distinct BCODEs); at least one HQ QTYMIN<0
- Members:
  - 08052347 — ไส้กรองเครื่อง เหล็ก ก.16NF (HQ QTYMIN=-1, HQ QTYOH2=0, SYP QTYOH2=0)
  - 08054824 — ไส้กรองเครื่อง เหล็ก ก.16NF (HQ QTYMIN=-1, HQ QTYOH2=1, SYP QTYOH2=0)
  - 08055225 — ไส้กรองเครื่อง เหล็ก ก.16NF (HQ QTYMIN=-1, HQ QTYOH2=0, SYP QTYOH2=0)
  - 08056362 — ไส้กรองเครื่อง เหล็ก ก.16NF (HQ QTYMIN=-1, HQ QTYOH2=0, SYP QTYOH2=0)
  - 08056502 — ไส้กรองเครื่อง เหล็ก ก.16NF (HQ QTYMIN=-1, HQ QTYOH2=1, SYP QTYOH2=0)
- Notes: PCODE twin/cluster — confirm not packaging variants before approve.
- Reviewer action: approve / reject / edit members

## Candidate group G171
- Confidence: med
- Evidence: same PCODE=C9NN7C094B (5 distinct BCODEs); at least one HQ QTYMIN<0
- Members:
  - 12050368 — เฟืองเกียร์ 3ชั้น (HQ QTYMIN=-1, HQ QTYOH2=0, SYP QTYOH2=0)
  - 12051038 — เฟืองเกียร์สี่ชั้นเฟืองบาง (HQ QTYMIN=-1, HQ QTYOH2=0, SYP QTYOH2=0)
  - 12052210 — เฟืองเกียร์สี่ชั้นเฟืองบาง (HQ QTYMIN=1, HQ QTYOH2=3, SYP QTYOH2=0)
  - 12053261 — เฟืองเกียร์สี่ชั้น เฟืองบาง (HQ QTYMIN=-1, HQ QTYOH2=1, SYP QTYOH2=0)
  - 12053540 — เฟืองเกียร์สี่ชั้นเฟืองบาง (HQ QTYMIN=-1, HQ QTYOH2=0, SYP QTYOH2=0)
- Notes: PCODE twin/cluster — confirm not packaging variants before approve.
- Reviewer action: approve / reject / edit members

## Candidate group G172
- Confidence: med
- Evidence: same PCODE=EDPN500B (5 distinct BCODEs); at least one HQ QTYMIN<0
- Members:
  - 12050696 — ชุดยางไฮปั้มแดง (HQ QTYMIN=-1, HQ QTYOH2=0, SYP QTYOH2=0)
  - 12050699 — ชุดยางไฮปั้มขาว (HQ QTYMIN=-1, HQ QTYOH2=0, SYP QTYOH2=0)
  - 12050774 — ชุดยางไฮปั้มแดง (HQ QTYMIN=-1, HQ QTYOH2=0, SYP QTYOH2=0)
  - 12051132 — ชุดยางไฮปั้มขาว (HQ QTYMIN=-1, HQ QTYOH2=0, SYP QTYOH2=0)
  - 12052328 — ชุดยางไฮปั้มขาว (HQ QTYMIN=1, HQ QTYOH2=3, SYP QTYOH2=1)
- Notes: PCODE twin/cluster — confirm not packaging variants before approve.
- Reviewer action: approve / reject / edit members

## Candidate group G173
- Confidence: med
- Evidence: same PCODE=MB012098 (5 distinct BCODEs); at least one HQ QTYMIN<0
- Members:
  - 11010249 — แม่ปั้มคลัชบน 5/8 (HQ QTYMIN=-1, HQ QTYOH2=0, SYP QTYOH2=0)
  - 11010658 — แม่ปั้มคลัชบน (HQ QTYMIN=-1, HQ QTYOH2=0, SYP QTYOH2=0)
  - 11019010 — แม่ปั๊มคลัชบน 5/8 (HQ QTYMIN=-1, HQ QTYOH2=0, SYP QTYOH2=0)
  - 11058670 — แม่ปั้มคลัชบน (HQ QTYMIN=-1, HQ QTYOH2=0, SYP QTYOH2=0)
  - 11058674 — แม่ปั้มคลัชบน (HQ QTYMIN=-1, HQ QTYOH2=0, SYP QTYOH2=0)
- Notes: PCODE twin/cluster — confirm not packaging variants before approve.
- Reviewer action: approve / reject / edit members

## Candidate group G174
- Confidence: med
- Evidence: same MCODE=08-HB6 (6 distinct BCODEs); at least one HQ QTYMIN<0
- Members:
  - 13012929 — สายแอร์เล็ก (S) (HQ QTYMIN=0, HQ QTYOH2=1, SYP QTYOH2=1)
  - 13012933 — สายแอร์เล็ก (S) (HQ QTYMIN=0, HQ QTYOH2=1, SYP QTYOH2=1)
  - 13012935 — สายแอร์เล็ก (S) (HQ QTYMIN=0, HQ QTYOH2=1, SYP QTYOH2=1)
  - 13012936 — สายแอร์เล็ก (S) (HQ QTYMIN=-1, HQ QTYOH2=0, SYP QTYOH2=1)
  - 13012937 — สายแอร์เล็ก (S) (HQ QTYMIN=-1, HQ QTYOH2=1, SYP QTYOH2=0)
  - 13012938 — สายแอร์เล็ก (S) (HQ QTYMIN=-1, HQ QTYOH2=1, SYP QTYOH2=0)
- Notes: MCODE twin/cluster — confirm factory cross-ref is mutual substitute.
- Reviewer action: approve / reject / edit members

## Candidate group G175
- Confidence: med
- Evidence: same MCODE=0K020 (6 distinct BCODEs); at least one HQ QTYMIN<0
- Members:
  - 08011371 — แหนบหลัง 2-4D (HQ QTYMIN=-1, HQ QTYOH2=0, SYP QTYOH2=0)
  - 08055587 — แหนบหลัง 2 หู (HQ QTYMIN=1, HQ QTYOH2=2, SYP QTYOH2=0)
  - 08055592 — แหนบหลัง 2 งอ (HQ QTYMIN=2, HQ QTYOH2=3, SYP QTYOH2=0)
  - 08055593 — แหนบหลัง 1 งอ (HQ QTYMIN=0, HQ QTYOH2=1, SYP QTYOH2=0)
  - 08055596 — แหนบหลัง รัด (HQ QTYMIN=-1, HQ QTYOH2=2, SYP QTYOH2=0)
  - 08055598 — แหนบหลัง รัด (HQ QTYMIN=-1, HQ QTYOH2=1, SYP QTYOH2=0)
- Notes: MCODE twin/cluster — confirm factory cross-ref is mutual substitute.
- Reviewer action: approve / reject / edit members

## Candidate group G176
- Confidence: med
- Evidence: same MCODE=10-08 (6 distinct BCODEs); at least one HQ QTYMIN<0
- Members:
  - 13050458 — แหวนทองแดง หัวฉีด (HQ QTYMIN=-1, HQ QTYOH2=0, SYP QTYOH2=0)
  - 13050459 — แหวนทองแดง (HQ QTYMIN=-1, HQ QTYOH2=0, SYP QTYOH2=0)
  - 13050460 — แหวนทองแดง (HQ QTYMIN=-1, HQ QTYOH2=0, SYP QTYOH2=0)
  - 13050463 — แหวนทองแดง มีขอบ (HQ QTYMIN=-1, HQ QTYOH2=0, SYP QTYOH2=0)
  - 13050464 — แหวนทองแดง มีขอบ (HQ QTYMIN=-1, HQ QTYOH2=0, SYP QTYOH2=0)
  - 13050465 — แหวนทองแดง มีขอบ (HQ QTYMIN=-1, HQ QTYOH2=0, SYP QTYOH2=0)
- Notes: MCODE twin/cluster — confirm factory cross-ref is mutual substitute.
- Reviewer action: approve / reject / edit members

## Candidate group G177
- Confidence: med
- Evidence: same MCODE=102949/10 (6 distinct BCODEs); at least one HQ QTYMIN<0
- Members:
  - 15010318 — ลูกปืนล้อหน้า (HQ QTYMIN=-1, HQ QTYOH2=0, SYP QTYOH2=0)
  - 15010319 — ลูกปืนล้อหน้า นอก (HQ QTYMIN=-1, HQ QTYOH2=0, SYP QTYOH2=0)
  - 15010329 — ลูกปืนล้อหน้า ใน (HQ QTYMIN=-1, HQ QTYOH2=0, SYP QTYOH2=0)
  - 15010970 — ลูกปืนล้อหน้า นอก (HQ QTYMIN=2, HQ QTYOH2=4, SYP QTYOH2=2)
  - 15011446 — ลูกปืนล้อหน้า นอก (HQ QTYMIN=-1, HQ QTYOH2=0, SYP QTYOH2=0)
  - 15021310 — ลูกปืนล้อหน้า นอก (HQ QTYMIN=-1, HQ QTYOH2=0, SYP QTYOH2=0)
- Notes: MCODE twin/cluster — confirm factory cross-ref is mutual substitute.
- Reviewer action: approve / reject / edit members

## Candidate group G178
- Confidence: med
- Evidence: same MCODE=104948/10 (6 distinct BCODEs); at least one HQ QTYMIN<0
- Members:
  - 15010129 — ลูกปืนล้อหน้า ใน (HQ QTYMIN=-1, HQ QTYOH2=0, SYP QTYOH2=0)
  - 15010321 — ลูกปืนล้อหน้า ใน (HQ QTYMIN=-1, HQ QTYOH2=0, SYP QTYOH2=0)
  - 15010322 — ลูกปืนล้อหน้า ใน (HQ QTYMIN=-1, HQ QTYOH2=1, SYP QTYOH2=0)
  - 15019510 — ลูกปืนล้อหน้า ใน (HQ QTYMIN=-1, HQ QTYOH2=0, SYP QTYOH2=0)
  - 15019511 — ลูกปืนล้อหน้า ใน (HQ QTYMIN=-1, HQ QTYOH2=0, SYP QTYOH2=0)
  - 15050302 — ลูกปืนล้อหน้า-ใน (HQ QTYMIN=1, HQ QTYOH2=4, SYP QTYOH2=2)
- Notes: MCODE twin/cluster — confirm factory cross-ref is mutual substitute.
- Reviewer action: approve / reject / edit members

## Candidate group G179
- Confidence: med
- Evidence: same MCODE=12.5x1100 (6 distinct BCODEs); at least one HQ QTYMIN<0
- Members:
  - 07010487 — สายพานพัดลม+ไดร์ชาร์ท (HQ QTYMIN=-1, HQ QTYOH2=0, SYP QTYOH2=0)
  - 07050784 — สายพานพัดลม+ไดชาร์ท (HQ QTYMIN=-1, HQ QTYOH2=0, SYP QTYOH2=0)
  - 13010376 — สายพาน 43" (HQ QTYMIN=-1, HQ QTYOH2=0, SYP QTYOH2=0)
  - 13019350 — สายพาน 42.5" (HQ QTYMIN=3, HQ QTYOH2=5, SYP QTYOH2=3)
  - 13019351 — สายพาน 42.5" (HQ QTYMIN=-1, HQ QTYOH2=0, SYP QTYOH2=?)
  - 13037000 — สายพาน 43" (HQ QTYMIN=-1, HQ QTYOH2=0, SYP QTYOH2=0)
- Notes: MCODE twin/cluster — confirm factory cross-ref is mutual substitute.
- Reviewer action: approve / reject / edit members

## Candidate group G180
- Confidence: med
- Evidence: same MCODE=12.5x975 (6 distinct BCODEs); at least one HQ QTYMIN<0
- Members:
  - 07050086 — สายพานแอร์ (HQ QTYMIN=-1, HQ QTYOH2=0, SYP QTYOH2=0)
  - 07050087 — สายพานแอร์ (HQ QTYMIN=0, HQ QTYOH2=1, SYP QTYOH2=1)
  - 07050785 — สายพานแอร์ (HQ QTYMIN=-1, HQ QTYOH2=0, SYP QTYOH2=0)
  - 13017610 — สายพาน 37.5" (HQ QTYMIN=2, HQ QTYOH2=6, SYP QTYOH2=4)
  - 13017631 — สายพาน 38" ร่องฟัน (HQ QTYMIN=-1, HQ QTYOH2=0, SYP QTYOH2=0)
  - 13036910 — สายพาน 38" (HQ QTYMIN=-1, HQ QTYOH2=0, SYP QTYOH2=0)
- Notes: MCODE twin/cluster — confirm factory cross-ref is mutual substitute.
- Reviewer action: approve / reject / edit members

## Candidate group G181
- Confidence: med
- Evidence: same MCODE=12649/10 (6 distinct BCODEs); at least one HQ QTYMIN<0
- Members:
  - 12010047 — ลูกปืนล้อหน้า เล็ก (HQ QTYMIN=-1, HQ QTYOH2=0, SYP QTYOH2=0)
  - 15010058 — ลูกปืนล้อหน้า นอก (HQ QTYMIN=-1, HQ QTYOH2=0, SYP QTYOH2=0)
  - 15010290 — ลูกปืนล้อหน้า นอก (HQ QTYMIN=-1, HQ QTYOH2=-1, SYP QTYOH2=0)
  - 15010917 — ลูกปืนล้อหน้า นอก (HQ QTYMIN=-1, HQ QTYOH2=0, SYP QTYOH2=0)
  - 15011295 — ลูกปืนล้อหน้า นอก all new 2wd (HQ QTYMIN=4, HQ QTYOH2=35, SYP QTYOH2=7)
  - 15018280 — ลูกปืนล้อหน้า นอก (HQ QTYMIN=-1, HQ QTYOH2=0, SYP QTYOH2=0)
- Notes: MCODE twin/cluster — confirm factory cross-ref is mutual substitute.
- Reviewer action: approve / reject / edit members

## Candidate group G182
- Confidence: med
- Evidence: same MCODE=21EPT-11/01R (6 distinct BCODEs); at least one HQ QTYMIN<0
- Members:
  - 13021125 — ฝาไฟสต๊อบแลมป์ (HQ QTYMIN=-1, HQ QTYOH2=0, SYP QTYOH2=0)
  - 13021126 — ฝาไฟสต๊อบแลมป์ (HQ QTYMIN=-1, HQ QTYOH2=0, SYP QTYOH2=0)
  - 13021127 — ฝาไฟสต๊อบแลมป์ (HQ QTYMIN=-1, HQ QTYOH2=0, SYP QTYOH2=0)
  - 13021128 — ฝาไฟสต๊อบแลมป์ (HQ QTYMIN=-1, HQ QTYOH2=0, SYP QTYOH2=0)
  - 13021129 — ฝาไฟสต๊อบแลมป์ (HQ QTYMIN=-1, HQ QTYOH2=0, SYP QTYOH2=0)
  - 13021131 — ฝาไฟสต๊อบแลมป์ (HQ QTYMIN=-1, HQ QTYOH2=0, SYP QTYOH2=0)
- Notes: MCODE twin/cluster — confirm factory cross-ref is mutual substitute.
- Reviewer action: approve / reject / edit members

## Candidate group G183
- Confidence: med
- Evidence: same MCODE=2343  2-2m (6 distinct BCODEs); at least one HQ QTYMIN<0
- Members:
  - 05017070 — แหวนลูกสูบ 73m หนา (HQ QTYMIN=-1, HQ QTYOH2=0, SYP QTYOH2=0)
  - 05028990 — แหวนลูกสูบ 73m หนา (HQ QTYMIN=-1, HQ QTYOH2=0, SYP QTYOH2=0)
  - 05030890 — แหวนลูกสูบ 73m หนา (HQ QTYMIN=-1, HQ QTYOH2=0, SYP QTYOH2=0)
  - 05034290 — แหวนลูกสูบ 73m หนา (HQ QTYMIN=-1, HQ QTYOH2=0, SYP QTYOH2=0)
  - 05034310 — แหวนลูกสูบ 73m หนา (HQ QTYMIN=-1, HQ QTYOH2=0, SYP QTYOH2=0)
  - 05034520 — แหวนลูกสูบ 73m หนา (HQ QTYMIN=-1, HQ QTYOH2=0, SYP QTYOH2=0)
- Notes: MCODE twin/cluster — confirm factory cross-ref is mutual substitute.
- Reviewer action: approve / reject / edit members

## Candidate group G184
- Confidence: med
- Evidence: same MCODE=25G00 (6 distinct BCODEs); at least one HQ QTYMIN<0
- Members:
  - 05016130 — แม่ปั้มเบรค (HQ QTYMIN=-1, HQ QTYOH2=0, SYP QTYOH2=0)
  - 05027110 — แหนบหลัง รัด (HQ QTYMIN=0, HQ QTYOH2=2, SYP QTYOH2=0)
  - 05027111 — แหนบหลัง (HQ QTYMIN=-1, HQ QTYOH2=0, SYP QTYOH2=0)
  - 05027112 — แหนบหลัง (HQ QTYMIN=-1, HQ QTYOH2=0, SYP QTYOH2=0)
  - 05027113 — แหนบหลัง (HQ QTYMIN=0, HQ QTYOH2=1, SYP QTYOH2=0)
  - 05027170 — แหนบหลัง (HQ QTYMIN=-1, HQ QTYOH2=0, SYP QTYOH2=0)
- Notes: MCODE twin/cluster — confirm factory cross-ref is mutual substitute.
- Reviewer action: approve / reject / edit members

## Candidate group G185
- Confidence: med
- Evidence: same MCODE=300849/11 (6 distinct BCODEs); at least one HQ QTYMIN<0
- Members:
  - 15014780 — ลูกปืนล้อหน้า นอก-ใน (HQ QTYMIN=-1, HQ QTYOH2=0, SYP QTYOH2=0)
  - 15014781 — ลูกปืนล้อหลัง ใน (HQ QTYMIN=-1, HQ QTYOH2=0, SYP QTYOH2=0)
  - 15015600 — ลูกปืนล้อหน้า นอก=ใน (HQ QTYMIN=1, HQ QTYOH2=2, SYP QTYOH2=2)
  - 15015601 — ลูกปืนล้อหน้า นอก=ใน (HQ QTYMIN=-1, HQ QTYOH2=0, SYP QTYOH2=0)
  - 15015603 — ลูกปืนล้อหน้า นอก=ใน (HQ QTYMIN=-1, HQ QTYOH2=0, SYP QTYOH2=0)
  - 15020300 — ลูกปืนล้อหน้า นอก-ใน (HQ QTYMIN=-1, HQ QTYOH2=0, SYP QTYOH2=0)
- Notes: MCODE twin/cluster — confirm factory cross-ref is mutual substitute.
- Reviewer action: approve / reject / edit members

## Candidate group G186
- Confidence: med
- Evidence: same MCODE=32218 (6 distinct BCODEs); at least one HQ QTYMIN<0
- Members:
  - 02017891 — แหวนรองลูกปืนล้อ (HQ QTYMIN=-1, HQ QTYOH2=0, SYP QTYOH2=0)
  - 02018810 — แหวนรองลูกปืนล้อหลัง (HQ QTYMIN=-1, HQ QTYOH2=0, SYP QTYOH2=0)
  - 15016030 — ลูกปืนล้อหลังใน (HQ QTYMIN=-1, HQ QTYOH2=0, SYP QTYOH2=0)
  - 15016031 — ลูกปืนล้อหลังใน (HQ QTYMIN=2, HQ QTYOH2=1, SYP QTYOH2=2)
  - 15017122 — ลูกปืนล้อหลัง นอก (HQ QTYMIN=-1, HQ QTYOH2=0, SYP QTYOH2=0)
  - 15018061 — ลูกปืนล้อหลังใน (HQ QTYMIN=-1, HQ QTYOH2=0, SYP QTYOH2=0)
- Notes: MCODE twin/cluster — confirm factory cross-ref is mutual substitute.
- Reviewer action: approve / reject / edit members

## Candidate group G187
- Confidence: med
- Evidence: same MCODE=4240A (6 distinct BCODEs); at least one HQ QTYMIN<0
- Members:
  - 09010283 — แหนบหลัง ซูโม่,โ18 (HQ QTYMIN=-1, HQ QTYOH2=0, SYP QTYOH2=0)
  - 09010284 — แหนบหลัง ซูโม่,F18 (HQ QTYMIN=-1, HQ QTYOH2=0, SYP QTYOH2=0)
  - 09010285 — แหนบหลัง ซูโม่,F18 (HQ QTYMIN=-1, HQ QTYOH2=0, SYP QTYOH2=0)
  - 09010286 — แหนบหลัง ซูโม่,F18 (HQ QTYMIN=-1, HQ QTYOH2=0, SYP QTYOH2=0)
  - 09010287 — แหนบหลัง ซูโม่,F18 (HQ QTYMIN=-1, HQ QTYOH2=0, SYP QTYOH2=0)
  - 09013930 — แหนบหลัง ซูโม่,F18 (HQ QTYMIN=-1, HQ QTYOH2=0, SYP QTYOH2=0)
- Notes: MCODE twin/cluster — confirm factory cross-ref is mutual substitute.
- Reviewer action: approve / reject / edit members

## Candidate group G188
- Confidence: med
- Evidence: same MCODE=550208 (6 distinct BCODEs); at least one HQ QTYMIN<0
- Members:
  - 09010297 — แหนบหน้า (HQ QTYMIN=-1, HQ QTYOH2=0, SYP QTYOH2=0)
  - 09010298 — แหนบหน้า (HQ QTYMIN=-1, HQ QTYOH2=0, SYP QTYOH2=0)
  - 09010299 — แหนบหน้า (HQ QTYMIN=-1, HQ QTYOH2=0, SYP QTYOH2=0)
  - 09016260 — แหนบหน้า (HQ QTYMIN=-1, HQ QTYOH2=0, SYP QTYOH2=0)
  - 09024950 — แหนบหน้า (HQ QTYMIN=-1, HQ QTYOH2=0, SYP QTYOH2=0)
  - 09024951 — แหนบหน้า (HQ QTYMIN=-1, HQ QTYOH2=0, SYP QTYOH2=0)
- Notes: MCODE twin/cluster — confirm factory cross-ref is mutual substitute.
- Reviewer action: approve / reject / edit members

## Candidate group G189
- Confidence: med
- Evidence: same MCODE=7PK-1473 (6 distinct BCODEs); at least one HQ QTYMIN<0
- Members:
  - 08013323 — สายพานพัดลม* Commuter (HQ QTYMIN=-1, HQ QTYOH2=0, SYP QTYOH2=0)
  - 08051656 — สายพานพัดลม (HQ QTYMIN=0, HQ QTYOH2=1, SYP QTYOH2=2)
  - 13010642 — สายพาน (HQ QTYMIN=-1, HQ QTYOH2=0, SYP QTYOH2=0)
  - 13011359 — สายพาน (HQ QTYMIN=-1, HQ QTYOH2=0, SYP QTYOH2=0)
  - 13011368 — สายพาน (HQ QTYMIN=-1, HQ QTYOH2=0, SYP QTYOH2=0)
  - 13050556 — สายพานพัดลม (HQ QTYMIN=0, HQ QTYOH2=3, SYP QTYOH2=2)
- Notes: MCODE twin/cluster — confirm factory cross-ref is mutual substitute.
- Reviewer action: approve / reject / edit members

## Candidate group G190
- Confidence: med
- Evidence: same MCODE=FX20 #305 (6 distinct BCODEs); at least one HQ QTYMIN<0
- Members:
  - 13011482 — ไฟฟ๊อกแลมป์ เหลี่ยม (HQ QTYMIN=-1, HQ QTYOH2=0, SYP QTYOH2=0)
  - 13011483 — ไฟฟ๊อกแลมป์ เหลี่ยม (HQ QTYMIN=-1, HQ QTYOH2=0, SYP QTYOH2=0)
  - 13011484 — ไฟฟ๊อกแลมป์ เหลี่ยม (HQ QTYMIN=-1, HQ QTYOH2=0, SYP QTYOH2=0)
  - 13011485 — ไฟฟ๊อกแลมป์ เหลี่ยม (HQ QTYMIN=-1, HQ QTYOH2=0, SYP QTYOH2=0)
  - 13011486 — ไฟฟ๊อกแลมป์ เหลี่ยม (HQ QTYMIN=-1, HQ QTYOH2=0, SYP QTYOH2=0)
  - 13011487 — ไฟฟ๊อกแลมป์ เหลี่ยม (HQ QTYMIN=-1, HQ QTYOH2=0, SYP QTYOH2=0)
- Notes: MCODE twin/cluster — confirm factory cross-ref is mutual substitute.
- Reviewer action: approve / reject / edit members

## Candidate group G191
- Confidence: med
- Evidence: same MCODE=KDH222 (6 distinct BCODEs); at least one HQ QTYMIN<0
- Members:
  - 08013096 — จานดิสเบรคหน้า ช่องลม 11.2" (HQ QTYMIN=0, HQ QTYOH2=2, SYP QTYOH2=0)
  - 08053798 — ฝาปิดตะขอลากรถ เหลี่ยม (HQ QTYMIN=-1, HQ QTYOH2=0, SYP QTYOH2=0)
  - 08053799 — ฝาปิดตะขอลากรถ เหลี่ยม (HQ QTYMIN=-1, HQ QTYOH2=0, SYP QTYOH2=0)
  - 08059772 — ไฟหน้า เสื้อ หลังคาสูง (HQ QTYMIN=-1, HQ QTYOH2=0, SYP QTYOH2=0)
  - 08059775 — PTขายึดใต้ไฟหน้า ไม่แยกขาย (HQ QTYMIN=-1, HQ QTYOH2=0, SYP QTYOH2=0)
  - 08059776 — ไฟหน้า เสื้อ หลังคาสูง (HQ QTYMIN=-1, HQ QTYOH2=0, SYP QTYOH2=0)
- Notes: MCODE twin/cluster — confirm factory cross-ref is mutual substitute.
- Reviewer action: approve / reject / edit members

## Candidate group G192
- Confidence: med
- Evidence: same MCODE=M238K (6 distinct BCODEs); at least one HQ QTYMIN<0
- Members:
  - 05010731 — ชาพอก (HQ QTYMIN=-1, HQ QTYOH2=0, SYP QTYOH2=0)
  - 05014000 — ชาพอก (HQ QTYMIN=-1, HQ QTYOH2=0, SYP QTYOH2=0)
  - 05014010 — ชาพอก (HQ QTYMIN=-1, HQ QTYOH2=0, SYP QTYOH2=0)
  - 05015910 — ชาพอก (HQ QTYMIN=-1, HQ QTYOH2=0, SYP QTYOH2=0)
  - 05035610 — ชาพอก (HQ QTYMIN=-1, HQ QTYOH2=0, SYP QTYOH2=0)
  - 05051794 — ชาพอก (HQ QTYMIN=-1, HQ QTYOH2=1, SYP QTYOH2=0)
- Notes: MCODE twin/cluster — confirm factory cross-ref is mutual substitute.
- Reviewer action: approve / reject / edit members

## Candidate group G193
- Confidence: med
- Evidence: same MCODE=R4650A (6 distinct BCODEs); at least one HQ QTYMIN<0
- Members:
  - 03010310 — ชาพก้าน 4JA1,4JH (HQ QTYMIN=1, HQ QTYOH2=2, SYP QTYOH2=0)
  - 03013210 — ชาพก้าน 4JA1-4JH (STD) (HQ QTYMIN=1, HQ QTYOH2=1, SYP QTYOH2=2)
  - 03014520 — ชาพก้าน 4JA1-4JH (HQ QTYMIN=-1, HQ QTYOH2=0, SYP QTYOH2=0)
  - 03022530 — ชาพก้าน 4JA1-4JH (HQ QTYMIN=-1, HQ QTYOH2=0, SYP QTYOH2=0)
  - 03052233 — ชาพก้าน 4JA1-4JH (HQ QTYMIN=0, HQ QTYOH2=1, SYP QTYOH2=0)
  - 03052234 — ชาพก้าน 4JA1-4JH (HQ QTYMIN=-1, HQ QTYOH2=0, SYP QTYOH2=0)
- Notes: MCODE twin/cluster — confirm factory cross-ref is mutual substitute.
- Reviewer action: approve / reject / edit members

## Candidate group G194
- Confidence: med
- Evidence: same MCODE=TR-710 (6 distinct BCODEs); at least one HQ QTYMIN<0
- Members:
  - 13012026 — หัวฉีดน้ำ (HQ QTYMIN=-1, HQ QTYOH2=0, SYP QTYOH2=0)
  - 13012029 — หัวฉีดน้ำ (HQ QTYMIN=-1, HQ QTYOH2=0, SYP QTYOH2=0)
  - 13012039 — หัวฉีดน้ำ (HQ QTYMIN=-1, HQ QTYOH2=0, SYP QTYOH2=0)
  - 13012041 — หัวฉีดน้ำ (HQ QTYMIN=-1, HQ QTYOH2=0, SYP QTYOH2=0)
  - 13012042 — หัวฉีดน้ำ (HQ QTYMIN=-1, HQ QTYOH2=0, SYP QTYOH2=0)
  - 13050014 — หัวฉีดน้ำ (HQ QTYMIN=-1, HQ QTYOH2=0, SYP QTYOH2=0)
- Notes: MCODE twin/cluster — confirm factory cross-ref is mutual substitute.
- Reviewer action: approve / reject / edit members

## Candidate group G195
- Confidence: med
- Evidence: same MCODE=Z2011 (6 distinct BCODEs); at least one HQ QTYMIN<0
- Members:
  - 06010790 — แหนบหลัง ตัวยาว 1 ไม่ปาด (HQ QTYMIN=-1, HQ QTYOH2=0, SYP QTYOH2=0)
  - 06011030 — แหนบหลัง ตัว 10x19" (HQ QTYMIN=-1, HQ QTYOH2=0, SYP QTYOH2=0)
  - 06011040 — แหนบหลัง ตัว 8x28" (HQ QTYMIN=-1, HQ QTYOH2=0, SYP QTYOH2=0)
  - 06011041 — แหนบหลัง ตัว 7รัด (HQ QTYMIN=-1, HQ QTYOH2=0, SYP QTYOH2=0)
  - 06011042 — แหนบหลัง ตัว 9 (HQ QTYMIN=-1, HQ QTYOH2=0, SYP QTYOH2=0)
  - 06012710 — แหนบหลัง ตัวยาว 1 ปาด (HQ QTYMIN=-1, HQ QTYOH2=0, SYP QTYOH2=0)
- Notes: MCODE twin/cluster — confirm factory cross-ref is mutual substitute.
- Reviewer action: approve / reject / edit members

## Candidate group G196
- Confidence: med
- Evidence: same MCODE=08-HB5 (5 distinct BCODEs); at least one HQ QTYMIN<0
- Members:
  - 13012950 — สายแอร์กลาง (M) (HQ QTYMIN=0, HQ QTYOH2=1, SYP QTYOH2=0)
  - 13012952 — สายแอร์กลาง (M) (HQ QTYMIN=0, HQ QTYOH2=1, SYP QTYOH2=1)
  - 13012953 — สายแอร์กลาง (M) (HQ QTYMIN=0, HQ QTYOH2=1, SYP QTYOH2=1)
  - 13012954 — สายแอร์กลาง (M) (HQ QTYMIN=-1, HQ QTYOH2=1, SYP QTYOH2=0)
  - 13012955 — สายแอร์กลาง (M) (HQ QTYMIN=0, HQ QTYOH2=1, SYP QTYOH2=1)
- Notes: MCODE twin/cluster — confirm factory cross-ref is mutual substitute.
- Reviewer action: approve / reject / edit members

## Candidate group G197
- Confidence: med
- Evidence: same MCODE=10480 (5 distinct BCODEs); at least one HQ QTYMIN<0
- Members:
  - 01013640 — ดอกจอก+เสื้อ (HQ QTYMIN=-1, HQ QTYOH2=0, SYP QTYOH2=0)
  - 03014170 — ลูกหมากปีกนกล่าง (HQ QTYMIN=-1, HQ QTYOH2=0, SYP QTYOH2=0)
  - 05024450 — ไฟเลี้ยวมุมสีขาว (HQ QTYMIN=-1, HQ QTYOH2=0, SYP QTYOH2=0)
  - 08018270 — เหล็กวัดน้ำมันเครื่อง (HQ QTYMIN=-1, HQ QTYOH2=0, SYP QTYOH2=0)
  - 09017020 — ปะเก็นชุดใหญ่ มีซีล ไม่มีฝา (HQ QTYMIN=-1, HQ QTYOH2=0, SYP QTYOH2=0)
- Notes: MCODE twin/cluster — confirm factory cross-ref is mutual substitute.
- Reviewer action: approve / reject / edit members

## Candidate group G198
- Confidence: med
- Evidence: same MCODE=105-85-10 (5 distinct BCODEs); at least one HQ QTYMIN<0
- Members:
  - 08010491 — ซีลข้อเหวี่ยงหลัง (HQ QTYMIN=-1, HQ QTYOH2=0, SYP QTYOH2=0)
  - 08011187 — ซีลข้อเหวี่ยงหลัง (HQ QTYMIN=-1, HQ QTYOH2=0, SYP QTYOH2=0)
  - 08043141 — ซีลข้อเหวี่ยงหลัง เหล็ก (HQ QTYMIN=-1, HQ QTYOH2=0, SYP QTYOH2=0)
  - 08051970 — ซีลข้อเหวี่ยงหลัง ล.เขียว (HQ QTYMIN=-1, HQ QTYOH2=0, SYP QTYOH2=0)
  - 08053831 — ซีลข้อเหวี่ยงหลัง ย.น้ำตาล (HQ QTYMIN=-1, HQ QTYOH2=0, SYP QTYOH2=0)
- Notes: MCODE twin/cluster — confirm factory cross-ref is mutual substitute.
- Reviewer action: approve / reject / edit members

## Candidate group G199
- Confidence: med
- Evidence: same MCODE=10Tx18T,23Tx20T (5 distinct BCODEs); at least one HQ QTYMIN<0
- Members:
  - 30051183 — แกน+จานเดือยหมูหน้า (HQ QTYMIN=-1, HQ QTYOH2=0, SYP QTYOH2=0)
  - 30052263 — แกน+จานเดือยหมูหน้า (HQ QTYMIN=-1, HQ QTYOH2=0, SYP QTYOH2=0)
  - 30052297 — แกน+จานเดือยหมูหน้า (HQ QTYMIN=-1, HQ QTYOH2=0, SYP QTYOH2=0)
  - 30052420 — แกน+จานเดือยหมูหน้า (HQ QTYMIN=-1, HQ QTYOH2=0, SYP QTYOH2=0)
  - 30052928 — แกน+จานเดือยหมูหน้า (HQ QTYMIN=2, HQ QTYOH2=4, SYP QTYOH2=1)
- Notes: MCODE twin/cluster — confirm factory cross-ref is mutual substitute.
- Reviewer action: approve / reject / edit members

## Candidate group G200
- Confidence: med
- Evidence: same MCODE=114.3-95.25-12T (5 distinct BCODEs); at least one HQ QTYMIN<0
- Members:
  - 02010293 — ซีลท้ายเกียร์ ฟูลเลอร์ (HQ QTYMIN=-1, HQ QTYOH2=0, SYP QTYOH2=0)
  - 02014410 — ซีลท้ายเกียร์ ฟูลเลอร์ (HQ QTYMIN=-1, HQ QTYOH2=0, SYP QTYOH2=0)
  - 02043640 — ซีลท้ายเกียร์ ฟูลเลอร์ (HQ QTYMIN=-1, HQ QTYOH2=0, SYP QTYOH2=0)
  - 02050041 — ซีลท้ายเกียร์ ฟูลเลอร์ 1K22560000 (HQ QTYMIN=-1, HQ QTYOH2=0, SYP QTYOH2=0)
  - 09050235 — ซีลท้ายเกียร์ ฟูลเลอร์ (HQ QTYMIN=-1, HQ QTYOH2=0, SYP QTYOH2=0)
- Notes: MCODE twin/cluster — confirm factory cross-ref is mutual substitute.
- Reviewer action: approve / reject / edit members

## Candidate group G201
- Confidence: med
- Evidence: same MCODE=11949/10 (5 distinct BCODEs); at least one HQ QTYMIN<0
- Members:
  - 15010192 — ลูกปืนล้อหน้า นอก (HQ QTYMIN=-1, HQ QTYOH2=0, SYP QTYOH2=0)
  - 15010560 — ลูกปืนล้อหน้า นอก (HQ QTYMIN=1, HQ QTYOH2=4, SYP QTYOH2=0)
  - 15017630 — ลูกปืนล้อหน้า นอก (HQ QTYMIN=-1, HQ QTYOH2=0, SYP QTYOH2=0)
  - 15017780 — ลูกปืนล้อหน้า นอก (HQ QTYMIN=-1, HQ QTYOH2=0, SYP QTYOH2=0)
  - 15050018 — ลูกปืนล้อหลัง นอก (HQ QTYMIN=-1, HQ QTYOH2=0, SYP QTYOH2=0)
- Notes: MCODE twin/cluster — confirm factory cross-ref is mutual substitute.
- Reviewer action: approve / reject / edit members

## Candidate group G202
- Confidence: med
- Evidence: same MCODE=12.5x1025 (5 distinct BCODEs); at least one HQ QTYMIN<0
- Members:
  - 05010147 — สายพานพัดลม (HQ QTYMIN=-1, HQ QTYOH2=0, SYP QTYOH2=0)
  - 07010112 — สายพานแอร์ (HQ QTYMIN=-1, HQ QTYOH2=0, SYP QTYOH2=0)
  - 13015840 — สายพาน 39.5" (HQ QTYMIN=3, HQ QTYOH2=7, SYP QTYOH2=2)
  - 13015841 — สายพาน 40" (HQ QTYMIN=-1, HQ QTYOH2=0, SYP QTYOH2=0)
  - 13015855 — สายพาน 39.5" (HQ QTYMIN=-1, HQ QTYOH2=-1, SYP QTYOH2=0)
- Notes: MCODE twin/cluster — confirm factory cross-ref is mutual substitute.
- Reviewer action: approve / reject / edit members

## Candidate group G203
- Confidence: med
- Evidence: same MCODE=12.5x925 (5 distinct BCODEs); at least one HQ QTYMIN<0
- Members:
  - 05050102 — สายพานแอร์ (HQ QTYMIN=-1, HQ QTYOH2=0, SYP QTYOH2=0)
  - 11010116 — สายพานแอร์ (HQ QTYMIN=-1, HQ QTYOH2=0, SYP QTYOH2=0)
  - 13017600 — สายพาน 35.5" (HQ QTYMIN=2, HQ QTYOH2=4, SYP QTYOH2=4)
  - 13017601 — สายพาน 36" (HQ QTYMIN=-1, HQ QTYOH2=0, SYP QTYOH2=0)
  - 13018060 — สายพานแอร์ 35.5" (HQ QTYMIN=1, HQ QTYOH2=5, SYP QTYOH2=1)
- Notes: MCODE twin/cluster — confirm factory cross-ref is mutual substitute.
- Reviewer action: approve / reject / edit members

---

## L-1 need orphans (HQ QTYMIN<0, SYP QTYOH2>0, no peer in groups above)

These need a substitute even if no peer was found yet. Top 80 by SYP on-hand.

| BCODE | DESCR | HQ QTYMIN | HQ QTYOH2 | SYP QTYOH2 |
|-------|-------|----------:|----------:|-----------:|
| 19025007 | หัวน็อต | -1 | -2252 | 326 |
| 13013312 | สายแอร์ กลาง | -1 | 0 | 99 |
| 13013313 | สายแอร์ เล็ก | -1 | 0 | 96 |
| 13013311 | สายแอร์ ใหญ่ | -1 | 0 | 95.7 |
| 19035001 | หัวน็อต | -1 | -1748.5 | 90 |
| 19045115 | แกนสกรู ไม่หัว | -1 | 46 | 75 |
| 13052638 | หลอดไฟ1จุด เล็ก | -1 | 0 | 71 |
| 24240000 | อะไหล่เก่า | -1 | -115 | 69 |
| 13050942 | หัวเสียบปลั๊กไฟหน้า | -1 | 0 | 49 |
| 19040001 | แกนสกรู ไม่หัว | -1 | -3 | 36 |
| 29012846 | หลอดไฟในเก๋ง | -1 | 0 | 30 |
| 19020005 | แกนสกรู ไม่หัว | -1 | -42 | 27 |
| 25020016 | ยางโอริง | -1 | 0 | 24 |
| 25025017 | ยางโอริง | -1 | -1 | 24 |
| 17014002 | หัวน็อตมิลดำ | -1 | -134 | 22 |
| 18050440 | แกนสกรู ไม่หัว | -1 | -21 | 22 |
| 19030002 | หัวน็อตกิโล | -1 | -213 | 22 |
| 13051931 | เข็มขัดรัดท่อยาง-ลวด | -1 | 11 | 20 |
| 18035001 | หัวน็อต | -1 | -208 | 20 |
| 13013631 | ฟิวส์หลอดแก้ว | -1 | 56 | 18 |
| 13013453 | หัวอัดจารบี ทองเหลือง | -1 | -1 | 17 |
| 14014657 | ใบตัดไฟเบอร์ | -1 | 4 | 16 |
| 32050284 | สกรูแทรค สี่เลี่ยม | -1 | -64 | 16 |
| 18040115 | แกนสกรู ไม่หัว | -1 | -15 | 14 |
| 12051921 | ไส้กรองโซล่า (สั้น) | -1 | 13 | 13 |
| 25040023 | ยางโอริง | -1 | 2 | 13 |
| 22010828 | น.ม.ฮ. เชลล์ | -1 | 29 | 11 |
| 28045203 | สกรูล้อหลังพ่วง LH | -1 | 0 | 11 |
| 01010255 | สกรูล้อหลัง สีเทา | -1 | 0 | 10 |
| 04050738 | สกรูล้อหลัง สีเทา | -1 | 0 | 10 |
| 04050739 | สกรูล้อหลัง สีเทา | -1 | 0 | 10 |
| 13010015 | ยางเบรคถ้วย | -1 | 0 | 10 |
| 13013305 | ข้อต่อตรงเสียบสายPVC | -1 | 0 | 10 |
| 13031659 | แหวนล็อคใน | -1 | 10 | 10 |
| 13051768 | เข็มขัดรัดท่อยาง-สแตนเลส | -1 | 56 | 10 |
| 13051776 | เข็มขัดรัดท่อยาง-เหล็กสีทอง | -1 | 30 | 10 |
| 14010823 | ลวดเชื่อมสแตนเลส | -1 | -25 | 10 |
| 14010904 | ลวดเชื่อมเฟือง | -1 | -2 | 10 |
| 14010905 | ลวดเชื่อมเฟือง | -1 | 3 | 10 |
| 19040036 | แกนสกรู ไม่หัว | -1 | 33 | 10 |
| 19040056 | แกนสกรู ไม่หัว | -1 | -10 | 10 |
| 19050223 | แกนสกรู ไม่หัว | -1 | -15 | 10 |
| 19050226 | แกนสกรู ไม่หัว | -1 | -11 | 10 |
| 25015071 | ยางโอริง | -1 | 2 | 10 |
| 25015130 | ยางโอริง | -1 | 0 | 10 |
| 25040015 | ยางโอริง | -1 | 3 | 10 |
| 25040036 | ยางโอริง | -1 | 7 | 10 |
| 25050030 | ยางโอริง | -1 | 10 | 10 |
| 25050183 | ยางโอริง | -1 | 0 | 10 |
| 28045200 | สกรูล้อหลังพ่วง RH | -1 | 0 | 10 |
| 13013306 | ข้อต่อตรงเสียบสายPVC | -1 | 0 | 9 |
| 13051784 | เข็มขัดรัดท่อยาง-เหล็ก | -1 | 31 | 9 |
| 13051936 | เข็มขัดรัดท่อยาง-ลวด | -1 | 41 | 9 |
| 13051938 | เข็มขัดรัดท่อยาง-ลวด | -1 | 8 | 9 |
| 17014052 | แกนสกรูมิลดำ ไม่หัว | -1 | -44 | 9 |
| 25035060 | ยางโอริง | -1 | 22 | 9 |
| 02050536 | ยางกันฝุ่นเบรค | -1 | 4 | 8 |
| 02050656 | น็อตหัวเพลา | -1 | 3 | 8 |
| 02050667 | สกรูล้อหลัง สีเทา RH 22x108 | -1 | 2 | 8 |
| 09011582 | สกรูล้อหลัง สีเทา | -1 | 6 | 8 |
| 13051394 | หลอดไฟแท้ | -1 | 1 | 8 |
| 13051756 | เข็มขัดรัดท่อยาง-ทะลุ | -1 | 73 | 8 |
| 13051826 | เข็มขัดรัดท่อยาง-สแตนเลส | -1 | 24 | 8 |
| 13051926 | เข็มขัดรัดท่อยาง-สแตนเลส | -1 | 36 | 8 |
| 13051939 | เข็มขัดรัดท่อยาง-ลวด | -1 | 44 | 8 |
| 13051946 | เข็มขัดรัดท่อยาง-ลวด | -1 | 10 | 8 |
| 13051951 | เข็มขัดรัดท่อยาง-ลวด | -1 | 13 | 8 |
| 13052075 | เข็มขัดรัดท่อยาง-สีทอง | -1 | 29 | 8 |
| 13052320 | ฟิวส์เสียบ | -1 | 20 | 8 |
| 17010007 | แกนสกรูมิลดำ ไม่หัว | -1 | -5 | 8 |
| 18040046 | แกนสกรูไม่มีหัว | -1 | -8 | 8 |
| 18040052 | สกรู ไม่พร้อมหัว | -1 | -8 | 8 |
| 22010752 | น.ม.ก. ptt | -1 | 22 | 8 |
| 25025095 | ยางโอริง | -1 | 8 | 8 |
| 30052983 | ใบมีดตัดหญ้า งอ | -1 | 0 | 8 |
| 16052452 | สายพานแบน | -1 | 0 | 7.1 |
| 02050698 | สกรูล้อหลังดัดแปลง | -1 | 0 | 7 |
| 02050699 | สกรูล้อหลังดัดแปลง | -1 | 0 | 7 |
| 09010052 | สกรูล้อหลัง รุ่นกล่องดำ | -1 | 0 | 7 |
| 13041432 | หัวเผา | -1 | 0 | 7 |

---

## REMARKS without extractable peer BCODE (sample, first 40)

Often brand-order (“ตราเพชร”) or free-text cross-ref without an 8-digit BCODE.

- `02010859` — ประเก็นฝาสูบ: _****ใช้ 6HE1ไม่เทอร์โบ แทนได้_
- `02050840` — สายเข้าเกียร์ 2เพลา ล-ห 3.25ม.: _ใช้แทน NO.463 ได้_
- `03014510` — ไฟส่องป้าย: _**ถ้าของหมดให้สั่งตราเพชรแทน**IS-038 YSR 28.-_
- `03014515` — ไฟส่องป้าย: _**ถ้าของหมดให้สั่งตราเพชรแทน**_
- `03022120` — ไฟในเก๋ง: _**ถ้าของหมดให้สั่งตราเพชรแทน**_
- `03052429` — ฝาไฟหรี่ในกันชน: _**ถ้าของหมดให้สั่งตราเพชรแทน**_
- `03052433` — ฝาไฟหรี่ในกันชน: _**ถ้าของหมดให้สั่งตราเพชรแทน**_
- `03052434` — ฝาไฟหรี่ในกันชน: _**ถ้าของหมดให้สั่งตราเพชรแทน**_
- `03052436` — ไฟตัดหมอก (เป็นชุด): _**ของหมดสั่งเป็นตราเพชรแทน**_
- `04016760` — ยางรีดน้ำ นอก: _ยาวกว่าJCM ใช้แทนJCMได้_
- `04050704` — ไดชาร์ท 24V 30A: _050503 = 050017-2 ใช้แทนกันได้_
- `04050734` — ไดชาร์ท 24V 45A: _8944559730/050503 = 050017-2 ใช้แทนกันได้_
- `05010708` — ไฟส่องป้าย: _**ถ้าของหมดให้สั่งเป็นตราเพชรแทน**_
- `05011300` — ไฟเลี้ยวข้าง: _**ถ้าของหมดให้สั่งเป็นตราเพชรแทน**_
- `05017710` — ฝาไฟหรี่ในกันชน: _**ถ้าของหมดให้สั่งเป็นตราเพชรแทน**_
- `05017720` — ฝาไฟหรี่ในกันชน: _**ถ้าของหมดให้สั่งเป็นตราเพชรแทน**_
- `05029310` — คลุมล้อหลัง: _แทน MD1600 COM. 8/41_
- `05051898` — เสื้อไฟหรี่มุม ฝาขาว: _**ถ้าของหมดให้สั่งเป็นตราเพชรแทน**_
- `05051899` — เสื้อไฟหรี่มุม: _**ถ้าของหมดให้สั่งเป็นตราเพชรแทน**_
- `05051905` — ไฟท้าย: _**ถ้าของหมดให้สั่งเป็นตราเพชรแทน**_
- `05051906` — ฝาไฟเลี้ยวข้าง: _**ถ้าของหมดให้สั่งเป็นตราเพชรแทน**_
- `08010400` — ไฟหรี่ในกันชน: _**ถ้าของหมดให้สั่งตราเพชรแทน**_
- `08010410` — ไฟหรี่ในกันชน: _**ถ้าของหมดให้สั่งตราเพชรแทน**_
- `08012520` — ไฟเลี้ยวข้าง: _**ถ้าของหมดให้สั่งเป็นตราเพชรแทน**_
- `08012625` — เฟืองเกียร์ 5 2ตัวชุด: _***  เร็วกว่า MTX ใช้แทนใด้_
- `08013460` — ไฟหรี่ในกันชนหน้า: _**ถ้าหมดแล้วให้สั่งตราเพชรแทน**_
- `08016770` — ไฟท้าย: _**ถ้าของหมดให้สั่งตราเพชรแทน**_
- `08016780` — ไฟท้าย: _**ถ้าของหมดให้สั่งตราเพชรแทน**_
- `08018910` — ไฟส่องป้าย: _**ถ้าของหมดให้สั่งตราเพชรแทน**_
- `08020200` — ไฟส่องป้าย: _**ถ้าของหมดให้สั่งตราเพชรแทน**_
- `08029600` — ไฟท้าย: _**ของหมดให้สั่งตราเพชรแทน**_
- `08052507` — ลูกสูบ86m 1.5-1.5-4m STD: _ไม่มีมา ใช้หัวเต็มแทนได้_
- `08055368` — ฝาไฟหรี่ในกันชน: _**ถ้าของหมดให้สั่งตราเพชรแทน**_
- `08055374` — ไฟตัดหมอก (เป็นชุด): _**ถ้าหมดให้สั่งเป็นตราเพชรแทน**_
- `08055375` — ไฟตัดหมอก (เป็นชุด): _**ถ้าของหมดให้สั่งเป็นตราเพชรแทน**_
- `08055376` — ไฟเลี้ยวข้าง ส้มลาย: _**ถ้าของหมดให้สั่งเป็นตราเพชรแทน**_
- `08055377` — ไฟเพดานเก๋ง: _**ถ้าหมดให้สั่งเป็นตราเพชรแทน**_
- `08055379` — ฝาไฟหรี่ในกันชน: _**ถ้าของหมดให้สั่งเป็นตราเพชรแทน**_
- `08055381` — ฝาไฟหรี่ในกันชน: _**ถ้าของหมดให้สั่งเป็นตราเพชรแทน**_
- `08055382` — ฝาไฟท้าย: _**ถ้าของหมดให้สั่งเป็นตราเพชรแทน**_
