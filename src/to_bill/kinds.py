from __future__ import annotations

PAY_LABELS = {
    "platform": "ชำระผ่านแพลตฟอร์ม",
    "cod": "เก็บเงินปลายทาง (COD)",
}


def normalize_kind(raw: str | None) -> str:
    return "rvo" if str(raw or "").strip().lower() == "rvo" else "to"


def series_for(kind: str | None) -> str:
    return "RVO" if normalize_kind(kind) == "rvo" else "TO"


def parse_pay_via(raw: str | None) -> str | None:
    text = str(raw or "").strip().lower()
    if not text:
        return None
    if text not in PAY_LABELS:
        raise ValueError("เลือกช่องทางชำระเงิน")
    return text


def pay_via_label(raw: str | None) -> str:
    return PAY_LABELS.get(str(raw or "").strip().lower(), "")
