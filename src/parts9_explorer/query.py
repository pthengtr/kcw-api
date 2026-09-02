from __future__ import annotations

import re
from dataclasses import dataclass, field

CODE1_LABELS = {
    "A": "ถ่าน", "C": "ซีล", "D": "บู๊ช", "E": "ลูกปืนเข็ม/กรงนก",
    "F": "ไส้กรองอากาศ", "G": "ยอยกากบาท", "I": "ลูกปืนตลับ", "K": "จานคลัช",
    "L": "สายอ่อน", "O": "โอริง", "P": "ไส้กรองน้ำมันเครื่อง", "Q": "ลูกหมาก", "R": "ลูกยาง",
}
CODE1_FROM_THAI = {
    "ถ่าน": "A", "ซีล": "C", "ซีลยาง": "C", "บู๊ช": "D", "บุช": "D",
    "ลูกปืนเข็ม": "E", "กรงนก": "E", "ไส้กรองอากาศ": "F", "ยอย": "G", "ยอยกากบาท": "G",
    "ลูกปืน": "I", "ลูกปืนตลับ": "I", "จานคลัช": "K", "สายอ่อน": "L",
    "โอริง": "O", "o-ring": "O", "oring": "O", "ไส้กรองน้ำมัน": "P", "ลูกหมาก": "Q", "ลูกยาง": "R",
}
SIZE_LABELS = {
    "A": ("สูง", "กว้าง", None), "C": ("ใน", "นอก", "หนา"), "D": ("ใน", "นอก", "หนา"),
    "E": ("ใน", "นอก", "หนา"), "F": ("ใน", "นอก", "สูง"), "G": ("ปลอก", "ยาว", None),
    "I": ("ใน", "นอก", "หนา"), "K": ("ยาว(นิ้ว)", "ฟัน", "ขนาดรูเฟือง"),
    "L": ("หัวสาย 1", "หัวสาย 2", "ยาว"), "O": ("ใน", "หนา", None), "P": ("ใน", "นอก", "สูง"),
    "Q": ("เตเปอร์", "แกนโต", None),  # ICMAS §7: Q SIZE slots still TBD in kcw-docs
    "R": ("ใน", "นอก", "หนา"),  # ICMAS §7: R SIZE slots still TBD; HQ data uses ใน/นอก/หนา pattern
}
# ICMAS SIZE1–3 are varchar; L uses hose-end codes (NN12) and lengths (13").
_SIZE_VALUE = r"[^\s]+"
_NUMERIC_TOKEN = re.compile(r"-?\d+(?:\.\d+)?")
CATEGORY_LABELS = {
    "01": "TX จิ๊ป แลนด์", "02": "I/S JCM บรรทุก 10 ล้อ", "03": "I/S D-MAX กระบะ",
    "04": "I/S ELF 4-6 ล้อ", "05": "NISSAN กระบะ เก๋ง", "06": "NISSAN UD บรรทุก",
    "07": "MAZDA FORD", "08": "TOYOTA", "09": "HINO", "10": "FUSO",
    "11": "MITSUBISHI", "12": "รถไถ FORD", "13": "ทั่วไป โช้ค ไฟ ยาง",
    "14": "เครื่องเหล็ก", "15": "ลูกปืน", "16": "HONDA ญี่ปุ่น เกาหลี",
    "17": "สกรู MIC ดำ", "18": "สกรู NF", "19": "สกรู NC", "20": "สกรู MIC ขาว",
    "21": "แบตเตอรี่", "22": "น้ำมัน จารบี", "23": "รถยุโรป", "24": "อะไหล่เก่า",
    "25": "ยางโอริง", "26": "สายอ่อน", "27": "บัส", "28": "พ่วง เทลเลอร์",
    "29": "ประดับยนต์", "30": "รถไถ KUBOTA", "31": "รถไถ MASSEY", "32": "แม็คโคร",
    "33": "อัดสายไฮดรอลิค", "34": "โฟคลิฟ", "35": "รถไถ ยันม่าร์",
    "40": "ค่าแรง", "70": "ค่าใช้จ่าย", "91": "โปรโมชั่น",
}
_DOC_HINT = re.compile(
    r"^(PI|PO|PV|RC|RV|RVI|KCPN|3T|3SA|8K|SA|TD|TR|TF|TFV|TAD|CN|DN)\w+",
    re.I,
)
# Internal BCODE is digits (optional letter suffix). Hyphenated values are OEM/PCODE.
_BCODE_LIKE = re.compile(r"^[0-9]{4,}[A-Za-z0-9]*$")
_CODE1_TOKEN = re.compile(r"^[A-Za-z]$")
_FIELD_PREFIX = re.compile(
    r"^(oem|pcode|mcode|เบอร์แท้|เบอร์โรงงาน|code1|ประเภท)[:\s]+",
    re.I,
)
_KIND_PREFIX = re.compile(
    r"^(si|pi|po|pv|rv|np|iclow|code_size|codesize|code-size|รหัสขนาด|"
    r"สินค้า|บิลขาย|บิลซื้อ|ใบสั่ง(?:ซื้อ)?|"
    r"ค้างรับ|ใบสำคัญจ่าย|ใบสำคัญรับ|โน้ต|ใบจ่าย|note)[:\s]+",
    re.I,
)
_KIND_ALIASES = {
    "si": "si", "บิลขาย": "si",
    "pi": "pi", "บิลซื้อ": "pi",
    "po": "po", "ใบสั่ง": "po", "ใบสั่งซื้อ": "po",
    "pv": "pv", "ใบสำคัญจ่าย": "pv", "โน้ต": "pv", "ใบจ่าย": "pv", "note": "pv", "np": "pv",
    "rv": "rv", "ใบสำคัญรับ": "rv",
    "iclow": "iclow", "ค้างรับ": "iclow",
    "สินค้า": "product",
    "code_size": "code_size", "codesize": "code_size", "code-size": "code_size",
    "รหัสขนาด": "code_size",
}
DOC_KIND_LABELS = {
    "si": "บิลขาย SI",
    "pi": "บิลซื้อ PI",
    "po": "ใบสั่งซื้อ PO",
    "pv": "ใบสำคัญจ่าย PV",
    "rv": "ใบสำคัญรับ RV",
    "iclow": "ค้างรับ ICLOW",
    "product": "สินค้า",
    "code_size": "รหัส+ขนาด",
}


def maybe_document_query(raw: str) -> bool:
    """Single token with digits — voucher, note, or bill number, including numeric notes."""
    q = (raw or "").strip()
    if not q or " " in q:
        return False
    compact = re.sub(r"\s+", "", q)
    return len(compact) >= 4 and any(ch.isdigit() for ch in compact)


def infer_doc_kind(docno: str) -> str | None:
    compact = re.sub(r"\s+", "", docno or "")
    if not compact:
        return None
    u = compact.upper()
    if u.startswith("PO"):
        return "po"
    if u.startswith(("KCPN", "PV")) or re.match(r"^P\d", u):
        return "pv"
    if u.startswith(("RC", "RV", "RVI")):
        return "rv"
    if u.startswith("PI"):
        return "pi"
    if u.startswith(("SA", "3SA", "8K", "3T", "TD", "TR", "TF", "TAD", "CN", "DN")):
        return "si"
    return None


@dataclass
class ParsedQuery:
    raw: str
    kind: str
    bcode_prefix: str | None = None
    code1: str | None = None
    sizes: list[str] = field(default_factory=list)
    text_terms: list[str] = field(default_factory=list)
    docno: str | None = None
    doc_kind: str | None = None
    want_product: bool = True
    search_mode: str | None = None
    size1: str | None = None
    size2: str | None = None
    size3: str | None = None


def category_label(bcode: str) -> str:
    code = (bcode or "").strip()
    if len(code) >= 2 and code[:2].isdigit():
        return CATEGORY_LABELS.get(code[:2], code[:2])
    return ""


def code1_label(code1: str | None) -> str:
    letter = (code1 or "").strip().upper()
    return CODE1_LABELS.get(letter, letter)


def size_labels(code1: str | None) -> tuple[str | None, str | None, str | None]:
    letter = (code1 or "").strip().upper()
    return SIZE_LABELS.get(letter, ("SIZE1", "SIZE2", "SIZE3"))


def _safe_size_value(value: object) -> str:
    if value is None:
        return ""
    s = str(value).strip()
    if not s or s.lower() == "nan":
        return ""
    return s


def format_size_line(
    code1: str | None,
    size1: object,
    size2: object,
    size3: object,
    *,
    compact: bool = False,
) -> str:
    """Label SIZE1–3 by CODE1 per kcw-docs ICMAS dictionary §7."""
    letter = (code1 or "").strip().upper()
    values = [_safe_size_value(size1), _safe_size_value(size2), _safe_size_value(size3)]
    if not any(values):
        return ""
    labels = SIZE_LABELS.get(letter)
    if not labels:
        shown = [v for v in values if v]
        return " / ".join(shown)
    pairs: list[str] = []
    for idx, label in enumerate(labels):
        if label and idx < len(values) and values[idx]:
            pairs.append(f"{label} {values[idx]}")
    if not pairs:
        shown = [v for v in values if v]
        return " / ".join(shown)
    sep = " | " if not compact else " / "
    body = sep.join(pairs)
    return body if compact else f"ขนาด: {body}"


def _extract_code1_token(text: str) -> str | None:
    """First CODE1 letter/thai alias in a code+size query."""
    for tok in [t for t in re.split(r"\s+", (text or "").strip()) if t]:
        low = tok.lower()
        if low in ("ขนาด", "size"):
            continue
        if tok in CODE1_FROM_THAI:
            return CODE1_FROM_THAI[tok]
        if _CODE1_TOKEN.match(tok) and tok.upper() in CODE1_LABELS:
            return tok.upper()
    return None


def _strip_size_patterns(text: str, code1: str | None = None) -> str:
    t = re.sub(
        r"(\d+(?:\.\d+)?)\s*[x×*]\s*(\d+(?:\.\d+)?)(?:\s*[x×*]\s*(\d+(?:\.\d+)?))?",
        " ",
        text or "",
        flags=re.I,
    )
    labels: list[str] = []
    if code1:
        labels.extend(l for l in SIZE_LABELS.get(code1.upper(), ()) if l)
    labels.extend(["size1", "size2", "size3", "ใน", "นอก", "หนา", "สูง", "ยาว"])
    seen: set[str] = set()
    for label in labels:
        key = label.lower()
        if key in seen:
            continue
        seen.add(key)
        t = re.sub(
            rf"(?:{re.escape(label)})\s*[:=]?\s*({_SIZE_VALUE})",
            " ",
            t,
            flags=re.I,
        )
    return t.strip()


def _parse_code_size_slots(text: str, code1: str | None) -> tuple[str | None, str | None, str | None]:
    """Parse SIZE1–3 using ICMAS labels for the resolved CODE1 (e.g. G: ปลอก/ยาว)."""
    letter = (code1 or "").strip().upper()
    labels = SIZE_LABELS.get(letter)
    if not labels:
        return None, None, None
    out: list[str | None] = [None, None, None]
    matched = False
    ordered = sorted(
        [(idx, label) for idx, label in enumerate(labels) if label and idx <= 2],
        key=lambda item: len(item[1]),
        reverse=True,
    )
    for idx, label in ordered:
        m = re.search(
            rf"(?:{re.escape(label)})\s*[:=]?\s*({_SIZE_VALUE})",
            text or "",
            re.I,
        )
        if m:
            out[idx] = m.group(1)
            matched = True
    return (out[0], out[1], out[2]) if matched else (None, None, None)


def _parse_size_slots(text: str) -> tuple[str | None, str | None, str | None]:
    s1 = s2 = s3 = None
    m1 = re.search(r"(?:size1|ใน|id|i\.?d\.?)\s*[:=]?\s*(\d+(?:\.\d+)?)", text, re.I)
    m2 = re.search(r"(?:size2|นอก|od|o\.?d\.?)\s*[:=]?\s*(\d+(?:\.\d+)?)", text, re.I)
    m3 = re.search(r"(?:size3|หนา|สูง|ยาว|width|thick)\s*[:=]?\s*(\d+(?:\.\d+)?)", text, re.I)
    if m1:
        s1 = m1.group(1)
    if m2:
        s2 = m2.group(1)
    if m3:
        s3 = m3.group(1)
    if not (s1 or s2 or s3):
        triple = re.search(
            r"(\d+(?:\.\d+)?)\s*[x×*]\s*(\d+(?:\.\d+)?)\s*[x×*]\s*(\d+(?:\.\d+)?)", text, re.I
        )
        pair = re.search(r"(\d+(?:\.\d+)?)\s*[x×*]\s*(\d+(?:\.\d+)?)", text, re.I)
        if triple:
            return triple.group(1), triple.group(2), triple.group(3)
        if pair:
            return pair.group(1), pair.group(2), None
    return s1, s2, s3


def _assign_numeric_size_slots(text: str) -> tuple[str | None, str | None, str | None]:
    nums = [t for t in re.split(r"\s+", text or "") if _NUMERIC_TOKEN.fullmatch(t)]
    if len(nums) >= 3:
        return nums[0], nums[1], nums[2]
    if len(nums) == 2:
        return nums[0], nums[1], None
    if len(nums) == 1:
        return nums[0], None, None
    return None, None, None


def parse_code_size_query(raw: str) -> ParsedQuery:
    """CODE1 + exact SIZE1/2/3 — ICMAS dictionary §7."""
    q = (raw or "").strip()
    if not q:
        return ParsedQuery(raw="", kind="product", search_mode="code_size")
    code1 = _extract_code1_token(q)
    size1, size2, size3 = _parse_code_size_slots(q, code1)
    if not (size1 or size2 or size3):
        size1, size2, size3 = _parse_size_slots(q)
    q_tokens = _strip_size_patterns(q, code1)
    tokens = [t for t in re.split(r"\s+", q_tokens) if t]
    text_terms: list[str] = []
    for tok in tokens:
        low = tok.lower()
        if low in ("ขนาด", "size"):
            continue
        if tok in CODE1_FROM_THAI:
            code1 = code1 or CODE1_FROM_THAI[tok]
            continue
        if _CODE1_TOKEN.match(tok) and tok.upper() in CODE1_LABELS:
            code1 = code1 or tok.upper()
            continue
        if re.fullmatch(r"-?\d+(?:\.\d+)?", tok):
            continue
        text_terms.append(tok)
    if not (size1 or size2 or size3):
        size1, size2, size3 = _assign_numeric_size_slots(q)
    sizes = [s for s in (size1, size2, size3) if s]
    return ParsedQuery(
        raw=q,
        kind="product",
        code1=code1,
        sizes=sizes[:3],
        size1=size1,
        size2=size2,
        size3=size3,
        text_terms=text_terms,
        want_product=True,
        search_mode="code_size",
    )


def code_size_query_valid(parsed: ParsedQuery) -> bool:
    has_size = bool(parsed.size1 or parsed.size2 or parsed.size3 or parsed.sizes)
    return bool(parsed.code1) and has_size


def parse_query(raw: str) -> ParsedQuery:
    q = (raw or "").strip()
    if not q:
        return ParsedQuery(raw="", kind="product")
    forced = None
    m = _KIND_PREFIX.match(q)
    if m:
        forced = _KIND_ALIASES.get(m.group(1).lower())
        q = q[m.end():].strip()
    if forced == "code_size":
        parsed = parse_code_size_query(q)
        return parsed
    field = None
    fm = _FIELD_PREFIX.match(q)
    if fm:
        field = fm.group(1).lower()
        q = q[fm.end():].strip()
        forced = forced or "product"
    compact = re.sub(r"\s+", "", q)
    if forced in ("si", "pi", "po", "pv", "rv", "iclow"):
        return ParsedQuery(
            raw=q, kind="document", docno=compact or None, doc_kind=forced, want_product=False,
        )
    if forced == "product":
        pass
    elif infer_doc_kind(compact) or _DOC_HINT.match(compact):
        return ParsedQuery(
            raw=q, kind="document", docno=compact,
            doc_kind=infer_doc_kind(compact), want_product=False,
        )
    if field in ("oem", "pcode", "mcode", "เบอร์แท้", "เบอร์โรงงาน") and q:
        return ParsedQuery(raw=q, kind="product", text_terms=[q], want_product=True)
    if _BCODE_LIKE.match(compact):
        return ParsedQuery(raw=q, kind="product", bcode_prefix=compact, want_product=True)
    tokens = [t for t in re.split(r"\s+", q) if t]
    code1 = None
    sizes: list[str] = []
    text_terms: list[str] = []
    for tok in tokens:
        low = tok.lower()
        if low in ("ขนาด", "size"):
            continue
        if tok in CODE1_FROM_THAI:
            code1 = CODE1_FROM_THAI[tok]
            continue
        if _CODE1_TOKEN.match(tok) and tok.upper() in CODE1_LABELS:
            code1 = tok.upper()
            continue
        if re.fullmatch(r"-?\d+(?:\.\d+)?", tok):
            sizes.append(tok)
            continue
        text_terms.append(tok)
    return ParsedQuery(
        raw=q, kind="product", code1=code1, sizes=sizes[:3], text_terms=text_terms,
        bcode_prefix=compact if compact.isdigit() and len(compact) >= 4 else None,
        want_product=True,
    )
