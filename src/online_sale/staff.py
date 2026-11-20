"""Legacy LINE display-name → legal name roster for old PARTS9 SALE strings.

New issues resolve by LINE user id via ops.staff_profiles (src.staff).
This module remains as a fallback for bills issued before the snapshot table.
"""

from __future__ import annotations

import re

# Full name, nick, LINE display / POS SALE codes (and loose aliases).
# POS cashier codes (MIAW, AUM, …) appear on SIMAS.SALE for older TAD/CNTAD.
_STAFF = (
    ("พรอนันต์ มานะ", "เจี๊ยบ", ("J€@฿", "เจี๊ยบ", "พรอนันต์")),
    ("ปิยะนุช นันตาบุตร", "เมย์", ("🅼🅾🅾🅼🅰🆈", "เมย์", "เมย", "ปิยะนุช", "may")),
    ("สราวุฒิ พิกุลแกม", "พี่นก", ("Nok Garage", "Nok Garage (KCW)", "พี่นก", "สราวุฒิ", "nok")),
    ("ณัชชา นึกแจ้ง", "มิ้น", ("M", "มิ้น", "ณัชชา")),
    ("ฉัตรชัย สุวรรณกูล", "หนุ่ย", ("หนุ่ย", "ฉัตรชัย")),
    ("จิดาภา กระจาย", "การ์ตูน", ("cartoonnnn", "cartoon", "การ์ตูน", "จิดาภา")),
    ("รณชัย พงษ์ปาน", "อ้น", ("Aon", "อ้น", "รณชัย")),
    (
        "ธนวรรณ เดชกุญชร",
        "มะเหมี่ยว",
        ("มะ'เหมี่ยว", "มะเหมี่ยว", "ธนวรรณ", "MIAW", "miaw"),
    ),
    ("ธิติ จันทร์พราหมณ์", "ช๊อปเปอร์", ("CHOPPUIS.1995", "ช๊อปเปอร์", "ธิติ", "chopper")),
    ("ศุภิสรา เดชกุญชร", "เบ้นซ์", ("Benz", "เบ้นซ์", "ศุภิสรา")),
    ("อาทิตยา หมื่นไสยาสน์", "พลอย", ("พลอยยี่", "พลอย", "อาทิตยา")),
    ("สุริยะ โกศัลยกุล", "บอส", ("Boss", "บอส", "สุริยะ")),
    ("วัจน์กร นาคทอง", "เบลล์", ("Bellla", "Bell", "เบลล์", "วัจน์กร")),
    ("กัญญาวีร์ ปิ่นทอง", "กวาง", ("ᴋᴀɴʏᴀᴡᴇᴇ", "กวาง", "กัญญาวีร์", "kanyawee")),
    ("มัญชุนันท์ คำลา", "อ้อน", ("Manchunannnnn", "อ้อน", "มัญชุนันท์", "aon", "manchunan")),
    ("อานนท์ ชูสวัสดิ์", "นุ", ("Nu", "นุ", "อานนท์")),
    ("จิตติมา ทิมเทศ", "อุ้ม", ("Aum", "อุ้ม", "จิตติมา", "aum", "AUM")),
    ("ญดาพร นิมวรรณ์", "อุ๋มอิ๋ม", ("อุ๋มอิ๋ม", "ญดาพร")),
    ("นพดล โกศัลยกุล", "บูม", ("Boom", "บูม", "นพดล")),
    ("นฤมล วิทยผโลทัย", "ผึ้ง", ("peung", "ผึ้ง", "นฤมล")),
    (
        "ณัฐพล วิทยผโลทัย",
        "ภู่",
        ("PHU Nattapon W.", "PHU", "phu", "ภู่", "ณัฐพล", "Nattapon"),
    ),
    (
        "มกรา มณีกุล",
        "ไอซ์",
        ("January Ice", "January", "Ice", "ไอซ์", "มกรา"),
    ),
)


def _fold(value: str) -> str:
    return "".join((value or "").casefold().split())


def _tokens(value: str) -> set[str]:
    raw = value or ""
    out = {_fold(raw)} if raw.strip() else set()
    for word in re.split(r"[\s\-_/.,|()]+", raw):
        cleaned = _fold(word)
        if cleaned:
            out.add(cleaned)
    return {t for t in out if t}


def match_staff(actor: str) -> dict | None:
    tokens = _tokens(actor)
    if not tokens:
        return None
    # POS stamps like "MIAW ICE" / "AUM SPNT" — match the cashier token first.
    first = _fold((actor or "").strip().split()[0]) if (actor or "").strip() else ""
    if first:
        tokens.add(first)
    for full_name, nick, aliases in _STAFF:
        alias_set = {_fold(a) for a in aliases} | {_fold(nick), _fold(full_name)}
        if tokens & alias_set:
            return {"full_name": full_name, "nick": nick}
        for token in tokens:
            for alias in alias_set:
                if len(alias) >= 4 and len(token) >= 4 and (
                    token.startswith(alias) or alias.startswith(token)
                ):
                    if alias.isascii() and token.isascii():
                        return {"full_name": full_name, "nick": nick}
    return None


def _label(full_name: str, nick: str) -> str:
    full = (full_name or "").strip()
    name = (nick or "").strip()
    if full and name:
        return f"{full} ({name})"
    return full or name


def issuer_full_name(actor: str) -> str:
    """Printed name: full name (nickname). Falls back to raw actor string."""
    hit = match_staff(actor)
    if hit:
        return _label(hit["full_name"], hit["nick"])
    return (actor or "").strip()


def issuer_document_name(actor: str) -> str:
    """Alias kept for call sites that want the document print format."""
    return issuer_full_name(actor)
