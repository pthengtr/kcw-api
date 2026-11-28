"""Thai copy for เฮียช้า cash-request chat."""

from __future__ import annotations


def ask_reason() -> str:
    return (
        "เบิกเงินเหรอ 😊\n"
        "ไหนบอกจ๋าหน่อย เอาไปทำอะไร เช่น ค่าน้ำมัน ค่าขนส่ง"
    )


def ask_amount() -> str:
    return (
        "โอเค 😊 จะเบิกเท่าไหร่?\n"
        "\n"
        "พิมพ์ตัวเลขมาได้เลย เช่น 500 (ไม่ต้องใส่คำว่าบาทหรือจุดทศนิยม)"
    )


def amount_invalid() -> str:
    return (
        "ใส่แค่ตัวเลขนะครับ เช่น 500\n"
        "ไม่ต้องมีบาท จุลภาค หรือจุดทศนิยมครับ"
    )


def reason_too_short() -> str:
    return "เหตุผลสั้นไปหน่อยครับ ขออีกนิด อย่างน้อย 3 ตัวอักษร"


def cancelled() -> str:
    return "ยกเลิกการเบิกแล้วครับ อยากเบิกใหม่พิมพ์ เบิกเงิน ได้เลย"


def pending_ack(
    *,
    short_code: int,
    amount: int,
    reason: str,
    notify_ok: bool = True,
) -> str:
    base = (
        f"รับเรื่องแล้วครับ (# {short_code})\n"
        f"เหตุผล: {reason}\n"
        f"จำนวน: {amount:,} บาท\n"
    )
    if notify_ok:
        return base + "เดี๋ยวเฮียส่งไปให้แอดมินดู — รอแป๊บนะ 🙏"
    return (
        base
        + "⚠️ ส่งหาแอดมินไม่สำเร็จตอนนี้ (โควต้าข้อความ LINE เต็มหรือระบบ push มีปัญหา)\n"
        f"แจ้งแอดมินให้พิมพ์ รายการเบิก หรือ อนุมัติ {short_code} ได้เลย"
    )


def resubmit_notify_failed(*, short_code: int) -> str:
    return (
        f"ได้บันทึกรายละเอียด #{short_code} แล้ว แต่ส่งหาแอดมินไม่สำเร็จครับ\n"
        f"แจ้งแอดมินให้พิมพ์ รายการเบิก หรือ อนุมัติ {short_code}"
    )


def resend_ok(*, short_code: int) -> str:
    return f"ส่งคำขอ #{short_code} หาแอดมินอีกครั้งแล้วครับ"


def resend_failed(*, short_code: int) -> str:
    return (
        f"ส่งคำขอ #{short_code} ไม่สำเร็จครับ (โควต้า LINE เต็มหรือ push มีปัญหา)\n"
        f"ให้แอดมินพิมพ์ รายการเบิก / อนุมัติ {short_code} แทนได้"
    )


def needs_info_prompt(*, short_code: int, admin_note: str) -> str:
    note = (admin_note or "").strip() or "ขอรายละเอียดเพิ่ม"
    return (
        f"แอดมินขอรายละเอียดเพิ่มสำหรับคำขอ #{short_code} ครับ:\n"
        f"{note}\n\n"
        "พิมพ์ตอบมาได้เลย — เฮียจะส่งต่อให้อีกรอบ"
    )


def resubmitted_ack(*, short_code: int) -> str:
    return (
        f"ได้เพิ่มรายละเอียดให้คำขอ #{short_code} แล้วครับ\n"
        "ส่งต่อแอดมินอีกรอบแล้ว รอแป๊บ 🙏"
    )


def approved_text(*, short_code: int, amount: int, voucher_num: str | None) -> str:
    """Compact approval notice; voucher code lives on the QR image, not in text."""
    _ = voucher_num
    return f"อนุมัติ #{short_code} ({amount:,}฿) แล้ว — สแกน QR ที่ตู้ Tiger ได้เลย"


def rejected_text(*, short_code: int, admin_note: str) -> str:
    note = (admin_note or "").strip() or "—"
    return (
        f"คำขอ #{short_code} ไม่ผ่านครับ\n"
        f"เหตุผล: {note}\n"
        "อยากเบิกใหม่พิมพ์ เบิกเงิน ได้เลย"
    )


def approve_ok(*, short_code: int) -> str:
    return f"อนุมัติ #{short_code} แล้ว — ส่ง QR ให้ผู้ขอแล้ว"


def approved_peer_notice(
    *,
    short_code: int,
    amount: int,
    reviewer_name: str | None,
    requester_name: str | None,
) -> str:
    who = (reviewer_name or "แอดมิน").strip() or "แอดมิน"
    req = (requester_name or "ผู้ขอ").strip() or "ผู้ขอ"
    return f"{who} อนุมัติ #{short_code} แล้ว ({amount:,}฿ · {req})"


def rejected_peer_notice(
    *,
    short_code: int,
    amount: int,
    reviewer_name: str | None,
    requester_name: str | None,
    admin_note: str | None = None,
) -> str:
    who = (reviewer_name or "แอดมิน").strip() or "แอดมิน"
    req = (requester_name or "ผู้ขอ").strip() or "ผู้ขอ"
    note = (admin_note or "").strip()
    base = f"{who} ปฏิเสธ #{short_code} แล้ว ({amount:,}฿ · {req})"
    if note:
        return f"{base}\nเหตุผล: {note}"
    return base


def needs_info_ok(*, short_code: int) -> str:
    return f"ส่งกลับ #{short_code} ให้ผู้ขอเพิ่มเหตุผลแล้วครับ"


def reject_ok(*, short_code: int) -> str:
    return f"ปฏิเสธ #{short_code} แล้วครับ"


def ask_admin_note(*, action: str, short_code: int) -> str:
    if action == "reject":
        return (
            f"ขอเหตุผลที่ไม่อนุมัติ #{short_code} หน่อยนะ 😊 "
            "จ๋าจะได้แจ้งคนที่ขอเบิก"
        )
    return f"ส่งกลับ #{short_code} — อยากให้ผู้ขอเติมอะไรเพิ่มครับ?"


def list_empty() -> str:
    return "ตอนนี้ไม่มีคำขอเบิกที่รออยู่ครับ 🎉"


def list_header() -> str:
    return "รายการเบิกที่รออยู่ครับ:"


def no_permission() -> str:
    return "บัญชีนี้ไม่มีสิทธิ์ใช้คำสั่งนี้ครับ"


def not_found(*, code: str) -> str:
    return f"ไม่พบคำขอ #{code} ครับ"


def bad_state(*, short_code: int, status: str) -> str:
    return f"คำขอ #{short_code} สถานะ {status} ทำรายการนี้ไม่ได้ครับ"


def voucher_failed(*, short_code: int, err: str) -> str:
    return (
        f"อนุมัติ #{short_code} แล้ว แต่สร้าง voucher ไม่สำเร็จครับ\n"
        f"({err})\n"
        "ลองใหม่อีกครั้งหรือเช็กค่า TIGER_VOUCHER_* บน Railway"
    )


def session_busy_other() -> str:
    return "กำลังอยู่ในขั้นตอนเบิกเงินอยู่ครับ พิมพ์ ยกเลิก ถ้าอยากเริ่มใหม่"


STATUS_TH = {
    "pending": "รออนุมัติ",
    "needs_info": "รอข้อมูลเพิ่ม",
    "approved": "อนุมัติแล้ว (รอถอน)",
    "rejected": "ปฏิเสธ",
    "cancelled": "ยกเลิก",
    "paid": "ถอนแล้ว",
}

VOUCHER_STATUS_TH = {
    "creating": "กำลังสร้าง",
    "pending": "รอสแกนถอน",
    "used": "ถอนแล้ว",
    "cancelled": "ยกเลิก voucher",
    "expired": "หมดอายุ",
    "failed": "สร้างไม่สำเร็จ",
}


def status_detail(
    *,
    short_code: int,
    request_status: str,
    amount: int,
    voucher_status: str | None,
    voucher_num: str | None,
) -> str:
    req = STATUS_TH.get(request_status, request_status)
    lines = [
        f"คำขอ #{short_code} · {amount:,} บาท",
        f"สถานะคำขอ: {req}",
    ]
    if voucher_status:
        vth = VOUCHER_STATUS_TH.get(voucher_status, voucher_status)
        lines.append(f"สถานะ voucher: {vth}")
    if voucher_num:
        lines.append(f"รหัส: {voucher_num}")
    if request_status == "approved" and voucher_status in {
        "creating",
        "pending",
        None,
        "",
    }:
        lines.append(f"ยกเลิกได้ด้วย: ยกเลิกเบิก {short_code}")
    return "\n".join(lines)


def cancel_ok(*, short_code: int) -> str:
    return f"ยกเลิก voucher ของคำขอ #{short_code} แล้วครับ"


def cancelled_requester(*, short_code: int) -> str:
    return (
        f"แอดมินยกเลิก QR ของคำขอ #{short_code} แล้วครับ\n"
        "สแกนตัวเดิมไม่ได้แล้ว — อยากเบิกใหม่พิมพ์ เบิกเงิน ได้เลย"
    )
