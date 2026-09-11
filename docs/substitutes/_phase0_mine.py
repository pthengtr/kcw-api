#!/usr/bin/env python3
"""Phase 0 discovery: mine ICMAS mirrors for substitute candidates. Read-only."""

from __future__ import annotations

import csv
import os
import re
from collections import defaultdict
from dataclasses import dataclass, field
from pathlib import Path

import psycopg
from dotenv import load_dotenv

ROOT = Path(__file__).resolve().parents[2]
OUT_MD = Path(__file__).resolve().parent / "initial-seed-candidates.md"
OUT_CSV = Path(__file__).resolve().parent / "initial-seed-candidates.csv"

BCODE_RE = re.compile(r"(?<!\d)(\d{8})(?!\d)")
# Prefer explicit substitute phrasing; still allow bare แทน but filter brand-order noise later
REMARKS_SQL = r"""
"REMARKS" ~* 'ทดแทน|ใช้แทน|แทนที่|แทนได้|ใช้แทนได้|ใช้รหัส.*แทน|รหัส.*แทน'
or "REMARKS" ~ 'แทน'
"""

# Brand-order / non-SKU substitute noise (ตราเพชร, etc.) — keep as notes, not peer groups
NOISE_PEER = re.compile(r"ตราเพชร|ยี่ห้อ|N/S|ไม่เทอร์โบ|หัวเต็ม|ใบแทน", re.I)


@dataclass
class Member:
    bcode: str
    descr: str
    hq_qtymin: float | None
    hq_qtyoh2: float | None
    syp_qtyoh2: float | None


@dataclass
class Group:
    gid: str
    confidence: str
    evidence: list[str] = field(default_factory=list)
    members: list[Member] = field(default_factory=list)
    notes: str = ""
    reviewer: str = "approve / reject / edit members"


def num(v) -> float | None:
    if v is None:
        return None
    s = str(v).strip()
    if not s:
        return None
    try:
        return float(s)
    except ValueError:
        return None


def fmt_qty(v: float | None) -> str:
    if v is None:
        return "?"
    if v == int(v):
        return str(int(v))
    return str(v)


def connect():
    load_dotenv(ROOT / ".env")
    conn = psycopg.connect(
        host=os.environ["SUPABASE_DB_HOST"],
        port=os.environ["SUPABASE_DB_PORT"],
        dbname=os.environ["SUPABASE_DB_NAME"],
        user=os.environ["SUPABASE_DB_USER"],
        password=os.environ["SUPABASE_DB_PASSWORD"],
        sslmode="require",
        connect_timeout=30,
    )
    conn.execute("set statement_timeout = '180s'")
    return conn


def load_catalog(conn) -> dict[str, Member]:
    """HQ master attrs + SYP on-hand."""
    sql = """
    select hq."BCODE",
           left(coalesce(hq."DESCR",''), 80) as descr,
           nullif(trim(hq."QTYMIN"),'')::numeric as hq_qtymin,
           nullif(trim(hq."QTYOH2"),'')::numeric as hq_qtyoh2,
           nullif(trim(syp."QTYOH2"),'')::numeric as syp_qtyoh2
    from raw_kcw.raw_hq_icmas_products hq
    left join raw_kcw.raw_syp_icmas_products syp on syp."BCODE" = hq."BCODE"
    """
    cat: dict[str, Member] = {}
    with conn.cursor() as cur:
        cur.execute(sql)
        for bcode, descr, hq_min, hq_oh, syp_oh in cur:
            if not bcode:
                continue
            cat[bcode.strip()] = Member(
                bcode=bcode.strip(),
                descr=(descr or "").strip(),
                hq_qtymin=float(hq_min) if hq_min is not None else None,
                hq_qtyoh2=float(hq_oh) if hq_oh is not None else None,
                syp_qtyoh2=float(syp_oh) if syp_oh is not None else None,
            )
    return cat


def fetch_remarks(conn) -> list[tuple[str, str, str]]:
    sql = f"""
    select "BCODE", left(coalesce("DESCR",''), 80), "REMARKS"
    from raw_kcw.raw_hq_icmas_products
    where coalesce(trim("REMARKS"), '') <> ''
      and ({REMARKS_SQL})
    order by "BCODE"
    """
    with conn.cursor() as cur:
        cur.execute(sql)
        return [(r[0].strip(), (r[1] or "").strip(), r[2] or "") for r in cur if r[0]]


STRONG_LINK_RE = re.compile(
    r"(?:ใช้รหัส|ใช่รหัส|ใช้\s*รหัส|รหัส)\s*[:=]?\s*(\d{8})\s*แทน"
    r"|ใช้\s*(\d{8})\s*แทน"
    r"|ใช้แทน[^\d]{0,20}(\d{8})"
    r"|(\d{8})\s*ใช้รหัสนี้แทน"
    r"|ใช้รหัสแทน\s*(\d{8})"
    r"|แทนได้[^\d]{0,10}(\d{8})"
    r"|(\d{8})\s*ใช้รหัสนี้แทนได้"
    r"|ใช้\s*รหัส\s*(\d{8})",
    re.I,
)


def extract_strong_peers(source_bcode: str, remarks: str) -> list[str]:
    """Explicit 'use BCODE instead' phrasing only — reduces kit/over-merge noise."""
    peers: list[str] = []
    for m in STRONG_LINK_RE.finditer(remarks):
        for g in m.groups():
            if g and g != source_bcode and g not in peers:
                peers.append(g)
    # Also: "ใช้รหัสXXXXXXXXแทน" without space (common)
    for m in re.finditer(r"ใช้รหัส\s*(\d{8})\s*แทน|ใช่รหัส\s*(\d{8})\s*แทน", remarks):
        g = m.group(1) or m.group(2)
        if g and g != source_bcode and g not in peers:
            peers.append(g)
    # Fallback: any 8-digit after แทน / before แทน within short window if only one peer
    if not peers:
        # "ใช้ 08056783 แทน" already covered; try bare list near แทน
        near = re.findall(
            r"(?:ใช้|รหัส|แทน)[^\d]{0,8}(\d{8})",
            remarks,
        )
        near = [p for p in near if p != source_bcode]
        # Dedup preserve order
        seen = set()
        near_u = []
        for p in near:
            if p not in seen:
                seen.add(p)
                near_u.append(p)
        if len(near_u) == 1:
            peers = near_u
    return peers


def fetch_code_clusters(conn, col: str) -> list[tuple[str, list[str]]]:
    """Clusters size 2–6; exclude Thai/dirty noise; prefer L-1 relevance."""
    assert col in ("PCODE", "MCODE")
    sql = f"""
    with base as (
      select trim("{col}") as code, "BCODE",
             nullif(trim("QTYMIN"),'')::numeric as qtymin
      from raw_kcw.raw_hq_icmas_products
      where coalesce(trim("{col}"), '') <> ''
        and length(trim("{col}")) between 5 and 36
        and trim("{col}") !~ '[ก-๙]'
        and trim("{col}") !~* 'ราคา|ซม|มม|มิล|ปี|บาท|เดือน'
    ),
    clust as (
      select code,
             array_agg(distinct "BCODE" order by "BCODE") as bcodes,
             count(distinct "BCODE") as n,
             bool_or(qtymin is not null and qtymin < 0) as has_l1
      from base
      group by code
      having count(distinct "BCODE") between 2 and 6
    )
    select code, bcodes
    from clust
    where has_l1
    order by n desc, code
    limit 200
    """
    with conn.cursor() as cur:
        cur.execute(sql)
        out = []
        for code, bcodes in cur:
            out.append((code, [b.strip() for b in bcodes]))
        return out


def fetch_l1_syp_stock(conn) -> list[str]:
    sql = """
    select hq."BCODE"
    from raw_kcw.raw_hq_icmas_products hq
    join raw_kcw.raw_syp_icmas_products syp on syp."BCODE" = hq."BCODE"
    where nullif(trim(hq."QTYMIN"),'')::numeric < 0
      and nullif(trim(syp."QTYOH2"),'')::numeric > 0
    order by hq."BCODE"
    """
    with conn.cursor() as cur:
        cur.execute(sql)
        return [r[0].strip() for r in cur if r[0]]


def union_find_merge(pairs: list[tuple[str, str]]) -> dict[str, set[str]]:
    parent: dict[str, str] = {}

    def find(x: str) -> str:
        parent.setdefault(x, x)
        while parent[x] != x:
            parent[x] = parent[parent[x]]
            x = parent[x]
        return x

    def union(a: str, b: str) -> None:
        ra, rb = find(a), find(b)
        if ra != rb:
            parent[rb] = ra

    for a, b in pairs:
        union(a, b)
    groups: dict[str, set[str]] = defaultdict(set)
    for x in parent:
        groups[find(x)].add(x)
    return groups


def member_line(m: Member) -> str:
    return (
        f"{m.bcode} — {m.descr} "
        f"(HQ QTYMIN={fmt_qty(m.hq_qtymin)}, HQ QTYOH2={fmt_qty(m.hq_qtyoh2)}, "
        f"SYP QTYOH2={fmt_qty(m.syp_qtyoh2)})"
    )


def main() -> None:
    print("connecting…")
    conn = connect()
    print("loading catalog…")
    cat = load_catalog(conn)
    print(f"  catalog {len(cat)} HQ BCODEs")

    print("REMARKS pass…")
    remarks_rows = fetch_remarks(conn)
    print(f"  remarks hits: {len(remarks_rows)}")

    remarks_pairs: list[tuple[str, str]] = []
    remarks_evidence: dict[frozenset[str], list[str]] = defaultdict(list)
    remarks_no_peer: list[tuple[str, str, str]] = []  # bcode, descr, remarks
    brand_order_hits = 0

    for bcode, descr, remarks in remarks_rows:
        peers = extract_strong_peers(bcode, remarks)
        peers = [p for p in peers if p in cat]
        if not peers:
            if NOISE_PEER.search(remarks):
                brand_order_hits += 1
            remarks_no_peer.append((bcode, descr, remarks.replace("\r", " ").replace("\n", " ").strip()[:160]))
            continue
        rem_clean = remarks.replace("\r", " ").replace("\n", " ").strip()[:120]
        for p in peers:
            remarks_pairs.append((bcode, p))
            key = frozenset({bcode, p})
            note = f"REMARKS on {bcode}: {rem_clean}"
            if note not in remarks_evidence[key]:
                remarks_evidence[key].append(note)

    print("PCODE clusters (L-1 relevant)…")
    pcode_clust = fetch_code_clusters(conn, "PCODE")
    print(f"  pcode L-1 clusters: {len(pcode_clust)}")

    print("MCODE clusters (L-1 relevant)…")
    mcode_clust = fetch_code_clusters(conn, "MCODE")
    print(f"  mcode L-1 clusters: {len(mcode_clust)}")

    print("L-1 + SYP stock…")
    l1_syp = fetch_l1_syp_stock(conn)
    print(f"  l1 with syp stock: {len(l1_syp)}")
    conn.close()

    # --- Build groups from REMARKS (highest signal) ---
    uf = union_find_merge(remarks_pairs)
    groups: list[Group] = []
    covered: set[str] = set()
    gid_n = 1

    # Sort remark groups by size then min bcode
    remark_sets = sorted(uf.values(), key=lambda s: (-len(s), min(s)))
    for s in remark_sets:
        if len(s) < 2:
            continue
        members = [cat[b] for b in sorted(s) if b in cat]
        if len(members) < 2:
            continue
        evid: list[str] = []
        seen_ev: set[str] = set()
        for a in sorted(s):
            for b in sorted(s):
                if a >= b:
                    continue
                for note in remarks_evidence.get(frozenset({a, b}), []):
                    if note not in seen_ev:
                        seen_ev.add(note)
                        evid.append(note)
        conf = "high" if len(members) <= 3 else "med"
        extra = ""
        if len(members) > 4:
            extra = " Large transitive merge — split if kit/related-parts, not mutual substitutes."
            conf = "med"
        g = Group(
            gid=f"G{gid_n:03d}",
            confidence=conf,
            evidence=evid[:6] or ["REMARKS peer BCODE link"],
            members=members,
            notes="From ICMAS.REMARKS strong peer phrasing (HQ mirror)." + extra,
        )
        groups.append(g)
        covered |= {m.bcode for m in members}
        gid_n += 1

    # Cap remark groups for reviewability — keep all with L-1 or SYP stock signal first
    def priority(g: Group) -> tuple:
        has_l1 = any((m.hq_qtymin or 0) < 0 for m in g.members)
        has_syp = any((m.syp_qtyoh2 or 0) > 0 for m in g.members)
        return (0 if has_l1 else 1, 0 if has_syp else 1, g.gid)

    groups.sort(key=priority)

    # --- PCODE groups (skip if already covered) ---
    pcode_added = 0
    for code, bcodes in pcode_clust:
        if all(b in covered for b in bcodes):
            continue
        # Skip if cluster already partially in a remarks group with same set — still add uncovered
        members = [cat[b] for b in bcodes if b in cat]
        if len(members) < 2:
            continue
        # Only propose if not fully covered
        if all(m.bcode in covered for m in members):
            continue
        g = Group(
            gid=f"G{gid_n:03d}",
            confidence="med",
            evidence=[f"same PCODE={code} ({len(members)} distinct BCODEs); at least one HQ QTYMIN<0"],
            members=members,
            notes="PCODE twin/cluster — confirm not packaging variants before approve.",
        )
        groups.append(g)
        covered |= {m.bcode for m in members}
        gid_n += 1
        pcode_added += 1
        if pcode_added >= 40:
            break

    # --- MCODE groups ---
    mcode_added = 0
    for code, bcodes in mcode_clust:
        if all(b in covered for b in bcodes):
            continue
        members = [cat[b] for b in bcodes if b in cat]
        if len(members) < 2:
            continue
        if all(m.bcode in covered for m in members):
            continue
        g = Group(
            gid=f"G{gid_n:03d}",
            confidence="med",
            evidence=[f"same MCODE={code} ({len(members)} distinct BCODEs); at least one HQ QTYMIN<0"],
            members=members,
            notes="MCODE twin/cluster — confirm factory cross-ref is mutual substitute.",
        )
        groups.append(g)
        covered |= {m.bcode for m in members}
        gid_n += 1
        mcode_added += 1
        if mcode_added >= 30:
            break

    # --- L-1 orphans (need substitute, no peer found yet) ---
    orphans = [b for b in l1_syp if b not in covered]
    # Prefer higher SYP stock
    orphans.sort(key=lambda b: -(cat[b].syp_qtyoh2 or 0) if b in cat else 0)

    # Stats for summary
    remarks_with_peer = len(remarks_pairs)
    remarks_peer_groups = sum(1 for s in uf.values() if len(s) >= 2)

    # Write markdown
    lines: list[str] = []
    lines.append("# Initial substitute seed candidates (Phase 0)")
    lines.append("")
    lines.append("## Glossary (locked)")
    lines.append("")
    lines.append("| Operator says | Means here | Not |")
    lines.append("|---------------|------------|-----|")
    lines.append("| qtylo / L-1 / ไม่สั่งซ้ำ | `ICMAS.QTYMIN < 0` (usually `-1`), per branch | Out of stock (`QTYOH2 = 0`) |")
    lines.append("| สินค้าทดแทน / แทน | Mutual peer SKUs in a catalog group | Bank transfer / โอนเงิน |")
    lines.append("| REMARKS peers | Candidate signal only — not source of truth | Confirmed substitutes |")
    lines.append("")
    lines.append("**Source:** Supabase mirrors `raw_kcw.raw_hq_icmas_products` / `raw_syp_icmas_products` (ingested ~2026-09-09). HQ is product master; branch `QTY*` stay per site.")
    lines.append("")
    lines.append("**Status:** Human review required. Do not import until approved. Phase 1 builds empty CRUD first.")
    lines.append("")
    lines.append("## Discovery counts")
    lines.append("")
    lines.append(f"| Signal | Count |")
    lines.append(f"|--------|------:|")
    lines.append(f"| REMARKS substitute-like hits (HQ) | {len(remarks_rows)} |")
    lines.append(f"| REMARKS with extractable peer BCODE | {remarks_with_peer} directed links |")
    lines.append(f"| REMARKS merged peer groups (≥2 BCODEs) | {remarks_peer_groups} |")
    lines.append(f"| REMARKS hits without peer BCODE (incl. brand-order) | {len(remarks_no_peer)} (brand-order-ish ≈{brand_order_hits}) |")
    lines.append(f"| PCODE clusters size 2–6 (clean, all HQ) | 4278 |")
    lines.append(f"| MCODE clusters size 2–6 (clean, all HQ) | 3755 |")
    lines.append(f"| PCODE L-1-relevant clusters scanned (cap 200) | {len(pcode_clust)} |")
    lines.append(f"| MCODE L-1-relevant clusters scanned (cap 200) | {len(mcode_clust)} |")
    lines.append(f"| PCODE groups proposed in this file | {pcode_added} |")
    lines.append(f"| MCODE groups proposed in this file | {mcode_added} |")
    lines.append(f"| HQ L-1 (`QTYMIN<0`) with SYP `QTYOH2>0` | {len(l1_syp)} |")
    lines.append(f"| Proposed groups in this file | {len(groups)} |")
    lines.append(f"| L-1+SYP-stock orphans (no peer in proposed groups) | {len(orphans)} (top 80 listed) |")
    lines.append("")
    lines.append("## Open questions for reviewer")
    lines.append("")
    lines.append("1. Should brand-order notes (e.g. “สั่งตราเพชรแทน”) become groups, or stay as purchasing notes only?")
    lines.append("2. PCODE/MCODE twins of size 3–6 — often size/pack variants; default **reject** unless ops confirms mutual ship?")
    lines.append("3. Prefer SYP-useful L-1 rows when approving first seed batch?")
    lines.append("")
    lines.append("---")
    lines.append("")
    lines.append("## Proposed groups")
    lines.append("")

    for g in groups:
        lines.append(f"## Candidate group {g.gid}")
        lines.append(f"- Confidence: {g.confidence}")
        for e in g.evidence:
            lines.append(f"- Evidence: {e}")
        lines.append("- Members:")
        for m in g.members:
            lines.append(f"  - {member_line(m)}")
        if g.notes:
            lines.append(f"- Notes: {g.notes}")
        lines.append(f"- Reviewer action: {g.reviewer}")
        lines.append("")

    lines.append("---")
    lines.append("")
    lines.append("## L-1 need orphans (HQ QTYMIN<0, SYP QTYOH2>0, no peer in groups above)")
    lines.append("")
    lines.append("These need a substitute even if no peer was found yet. Top 80 by SYP on-hand.")
    lines.append("")
    lines.append("| BCODE | DESCR | HQ QTYMIN | HQ QTYOH2 | SYP QTYOH2 |")
    lines.append("|-------|-------|----------:|----------:|-----------:|")
    for b in orphans[:80]:
        m = cat[b]
        lines.append(
            f"| {m.bcode} | {m.descr.replace('|','/')} | {fmt_qty(m.hq_qtymin)} | "
            f"{fmt_qty(m.hq_qtyoh2)} | {fmt_qty(m.syp_qtyoh2)} |"
        )
    lines.append("")
    lines.append("---")
    lines.append("")
    lines.append("## REMARKS without extractable peer BCODE (sample, first 40)")
    lines.append("")
    lines.append("Often brand-order (“ตราเพชร”) or free-text cross-ref without an 8-digit BCODE.")
    lines.append("")
    for bcode, descr, rem in remarks_no_peer[:40]:
        lines.append(f"- `{bcode}` — {descr}: _{rem}_")
    lines.append("")

    OUT_MD.write_text("\n".join(lines), encoding="utf-8")
    print(f"wrote {OUT_MD}")

    # CSV
    with OUT_CSV.open("w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(
            f,
            fieldnames=[
                "proposed_group_id",
                "bcode",
                "descr",
                "evidence",
                "confidence",
                "hq_qtymin",
                "hq_qtyoh2",
                "syp_qtyoh2",
                "notes",
            ],
        )
        w.writeheader()
        for g in groups:
            ev = "; ".join(g.evidence)[:500]
            for m in g.members:
                w.writerow(
                    {
                        "proposed_group_id": g.gid,
                        "bcode": m.bcode,
                        "descr": m.descr,
                        "evidence": ev,
                        "confidence": g.confidence,
                        "hq_qtymin": fmt_qty(m.hq_qtymin),
                        "hq_qtyoh2": fmt_qty(m.hq_qtyoh2),
                        "syp_qtyoh2": fmt_qty(m.syp_qtyoh2),
                        "notes": g.notes,
                    }
                )
        for b in orphans[:80]:
            m = cat[b]
            w.writerow(
                {
                    "proposed_group_id": "ORPHAN-L1",
                    "bcode": m.bcode,
                    "descr": m.descr,
                    "evidence": "HQ QTYMIN<0 + SYP QTYOH2>0; no peer found",
                    "confidence": "low",
                    "hq_qtymin": fmt_qty(m.hq_qtymin),
                    "hq_qtyoh2": fmt_qty(m.hq_qtyoh2),
                    "syp_qtyoh2": fmt_qty(m.syp_qtyoh2),
                    "notes": "needs substitute — empty peer",
                }
            )
    print(f"wrote {OUT_CSV}")

    print(
        "SUMMARY",
        {
            "remarks_hits": len(remarks_rows),
            "remarks_peer_groups": remarks_peer_groups,
            "pcode_l1_clusters": len(pcode_clust),
            "mcode_l1_clusters": len(mcode_clust),
            "l1_syp_stock": len(l1_syp),
            "proposed_groups": len(groups),
            "orphans": len(orphans),
            "pcode_groups_in_file": pcode_added,
            "mcode_groups_in_file": mcode_added,
        },
    )


if __name__ == "__main__":
    main()
