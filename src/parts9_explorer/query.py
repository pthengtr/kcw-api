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
}
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
_DOC_HINT = re.compile(r"^(P|PV|RC|RV|KCPN|PO|3T|3SA|SA|TD|TR|CN)\w+$", re.I)
_BCODE_LIKE = re.compile(r"^[0-9]{4,}[A-Za-z0-9\-]*$")
_CODE1_TOKEN = re.compile(r"^[A-Za-z]$")


@dataclass
class ParsedQuery:
    raw: str
    kind: str
    bcode_prefix: str | None = None
    code1: str | None = None
    sizes: list[str] = field(default_factory=list)
    text_terms: list[str] = field(default_factory=list)
    docno: str | None = None


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


def parse_query(raw: str) -> ParsedQuery:
    q = (raw or "").strip()
    if not q:
        return ParsedQuery(raw="", kind="product")
    compact = re.sub(r"\s+", "", q)
    if _DOC_HINT.match(compact) or (
        len(compact) >= 6
        and any(ch.isdigit() for ch in compact)
        and " " not in q.strip()
        and not _BCODE_LIKE.match(compact)
        and any(c.isalpha() for c in compact)
    ):
        return ParsedQuery(raw=q, kind="document", docno=compact)
    if _BCODE_LIKE.match(compact):
        return ParsedQuery(raw=q, kind="product", bcode_prefix=compact)
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
    )
