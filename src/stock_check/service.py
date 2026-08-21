from __future__ import annotations

import json
import time
from datetime import datetime
from typing import Any
from zoneinfo import ZoneInfo

from src.stock_check.config import StockCheckSettings, get_stock_check_settings
from src.stock_check.daily_pick import pick_daily_products
from src.stock_check.db_local import LocalStore
from src.stock_check.parts9 import (
    get_product_by_bcode,
    get_products_by_bcodes,
    list_stock_movements,
    lookup_products,
)
from src.stock_check.sa_writer import Parts9WriteError, post_stock_adjustment

BANGKOK = ZoneInfo("Asia/Bangkok")


class StockCheckService:
    def __init__(
        self,
        settings: StockCheckSettings | None = None,
        store: LocalStore | None = None,
    ):
        self.settings = settings or get_stock_check_settings()
        self.store = store or LocalStore(self.settings.sqlite_path)

    @staticmethod
    def _line_id(session: dict[str, Any]) -> str:
        return str(session.get("line_user_id") or "").strip()

    @staticmethod
    def _assert_can_approve(draft: dict[str, Any], session: dict[str, Any]) -> None:
        if StockCheckService._line_id(session) == str(draft.get("operator_line_user_id") or "").strip():
            raise PermissionError("cannot approve own draft")

    def _record_work(
        self,
        session: dict[str, Any],
        event_type: str,
        *,
        bcode: str | None = None,
        draft_id: str | None = None,
        variance: float | None = None,
        source: str | None = None,
    ) -> None:
        self.store.record_work_event(
            line_user_id=self._line_id(session),
            display_name=str(session.get("display_name") or ""),
            event_type=event_type,
            bcode=bcode,
            draft_id=draft_id,
            variance=variance,
            source=source,
        )

    def expire(self) -> None:
        self.store.expire_stale_leases()

    def take_n(self, session_id: str, count: int, *, with_stock_only: bool = True) -> list[dict[str, Any]]:
        """Lease next SKUs using weighted everyday ABC / risk groups."""
        del with_stock_only
        self.expire()
        count = max(1, min(int(count), 50))
        held = self.store.active_leased_bcodes()
        pending = {d["bcode"] for d in self.store.list_pending_drafts()}
        exclude = held | pending
        now = time.time()
        audits = self.store.get_local_audits()
        picked = pick_daily_products(
            count=count,
            exclude_bcodes=exclude,
            audits=audits,
            now=now,
        )
        idle = self.settings.lease_idle_seconds
        lease_items = [
            {
                "bcode": p.bcode,
                "pick_priority": flags.priority,
                "pick_reasons": list(flags.reasons),
                "abc_class": flags.abc_class,
                "sales_days_90": flags.sales_days_90,
            }
            for p, flags in picked
        ]
        claimed = self.store.claim_leases(
            session_id=session_id,
            lease_items=lease_items,
            lease_ttl=idle,
            now=now,
        )
        self.store.extend_leases(session_id, lease_ttl=idle, now=now)
        by_code = {p.bcode: (p, flags) for p, flags in picked}
        cards: list[dict[str, Any]] = []
        for bcode in claimed:
            item = by_code.get(bcode)
            if not item:
                continue
            product, flags = item
            card = self._product_card(product, audits.get(bcode))
            card["pick_priority"] = flags.priority
            card["pick_reasons"] = list(flags.reasons)
            card["abc_class"] = flags.abc_class
            card["sales_days_90"] = flags.sales_days_90
            cards.append(card)
        return cards

    def bump_leases(self, session_id: str) -> int:
        self.expire()
        return self.store.extend_leases(
            session_id,
            lease_ttl=self.settings.lease_idle_seconds,
        )

    def leased_list(self, session_id: str) -> list[dict[str, Any]]:
        self.expire()
        leases = self.store.list_leases_for_session(session_id)
        if not leases:
            return []
        self.store.extend_leases(session_id, lease_ttl=self.settings.lease_idle_seconds)
        audits = self.store.get_local_audits([row["bcode"] for row in leases])
        cards: list[dict[str, Any]] = []
        for row in leases:
            product = get_product_by_bcode(row["bcode"])
            if not product:
                continue
            card = self._product_card(product, audits.get(product.bcode))
            self._apply_lease_pick_meta(card, row)
            cards.append(card)
        return cards

    @staticmethod
    def _apply_lease_pick_meta(card: dict[str, Any], lease: dict[str, Any]) -> None:
        prio = lease.get("pick_priority")
        if prio is not None:
            try:
                card["pick_priority"] = int(prio)
            except (TypeError, ValueError):
                pass
        raw_reasons = lease.get("pick_reasons")
        if raw_reasons:
            if isinstance(raw_reasons, list):
                card["pick_reasons"] = raw_reasons
            else:
                try:
                    card["pick_reasons"] = json.loads(str(raw_reasons))
                except json.JSONDecodeError:
                    card["pick_reasons"] = [str(raw_reasons)]
        if lease.get("abc_class"):
            card["abc_class"] = lease["abc_class"]
        if lease.get("sales_days_90") is not None:
            card["sales_days_90"] = lease["sales_days_90"]

    def _assert_can_submit(self, *, session_id: str, bcode: str) -> None:
        if self.store.get_pending_draft_for_bcode(bcode):
            raise ValueError("สินค้านี้รออนุมัติอยู่แล้ว — รอผู้อนุมัติก่อน")
        lease = self.store.get_active_lease_for_bcode(bcode)
        if lease and lease["session_id"] != session_id:
            raise ValueError("มีพนักงานคนอื่นกำลังนับสินค้านี้อยู่")

    def _submission_flags(self, bcode: str, session_id: str | None) -> dict[str, Any]:
        pending = self.store.get_pending_draft_for_bcode(bcode)
        lease = self.store.get_active_lease_for_bcode(bcode)
        leased_elsewhere = bool(
            lease and session_id and lease["session_id"] != session_id
        )
        has_pending = pending is not None
        blocked = has_pending or leased_elsewhere
        reason = None
        if has_pending:
            reason = "สินค้านี้รออนุมัติอยู่แล้ว — รอผู้อนุมัติก่อน"
        elif leased_elsewhere:
            reason = "มีพนักงานคนอื่นกำลังนับสินค้านี้อยู่"
        return {
            "leased_elsewhere": leased_elsewhere,
            "has_pending_draft": has_pending,
            "submit_blocked": blocked,
            "block_reason": reason,
        }

    def _product_card(self, product, audit: dict | None) -> dict[str, Any]:
        data = product.as_dict()
        if audit:
            data["last_audited_at"] = audit["last_audited_at"]
            data["last_audited_by"] = audit["last_audited_by"]
            data["last_outcome"] = audit.get("last_outcome")
        else:
            data["last_audited_at"] = None
            data["last_audited_by"] = None
            data["last_outcome"] = None
        return data

    def attach_product_model(self, drafts: list[dict[str, Any]]) -> list[dict[str, Any]]:
        codes = {str(d.get("bcode") or "").strip() for d in drafts}
        codes.discard("")
        if not codes:
            return drafts
        by_code = {p.bcode: p for p in get_products_by_bcodes(codes)}
        for draft in drafts:
            product = by_code.get(str(draft.get("bcode") or "").strip())
            if product and product.model:
                draft["model"] = product.model
        return drafts

    def product_detail(self, bcode: str, *, session_id: str | None = None) -> dict[str, Any] | None:
        product = get_product_by_bcode(bcode)
        if not product:
            return None
        audit = self.store.get_local_audits([product.bcode]).get(product.bcode)
        card = self._product_card(product, audit)
        if session_id:
            self.bump_leases(session_id)
            for row in self.store.list_leases_for_session(session_id):
                if row["bcode"] == product.bcode:
                    self._apply_lease_pick_meta(card, row)
                    break
            card.update(self._submission_flags(product.bcode, session_id))
        return card

    def lookup(self, query: str, *, session_id: str | None = None) -> list[dict[str, Any]]:
        products = lookup_products(query)
        audits = self.store.get_local_audits([p.bcode for p in products])
        out = []
        for product in products:
            card = self._product_card(product, audits.get(product.bcode))
            card.update(self._submission_flags(product.bcode, session_id))
            out.append(card)
        return out

    def submit_count(
        self,
        *,
        session: dict[str, Any],
        bcode: str,
        counted_qty: float | None = None,
        difference: float | None = None,
        mark_correct: bool = False,
        source: str = "batch",
        notes: str | None = None,
    ) -> dict[str, Any]:
        self.expire()
        product = get_product_by_bcode(bcode)
        if not product:
            raise ValueError("product not found")

        self._assert_can_submit(session_id=session["id"], bcode=product.bcode)

        system_qty = float(product.qtyoh2)
        if mark_correct:
            counted = system_qty
            entry_mode = "correct"
        elif difference is not None:
            counted = system_qty + float(difference)
            entry_mode = "difference"
        elif counted_qty is not None:
            counted = float(counted_qty)
            entry_mode = "total"
        else:
            raise ValueError("provide counted_qty, difference, or mark_correct")

        variance = counted - system_qty
        operator_id = self._line_id(session)
        operator_name = session["display_name"]
        self.bump_leases(session["id"])

        if abs(variance) < 1e-9:
            draft_id = self.store.create_draft(
                {
                    "bcode": product.bcode,
                    "descr": product.descr,
                    "location1": product.location1,
                    "location2": product.location2,
                    "system_qty": system_qty,
                    "counted_qty": counted,
                    "variance": 0.0,
                    "entry_mode": entry_mode,
                    "source": source,
                    "status": "completed",
                    "operator_line_user_id": operator_id,
                    "operator_name": operator_name,
                    "notes": notes,
                    "completed_at": time.time(),
                }
            )
            self.store.upsert_local_audit(
                bcode=product.bcode,
                audited_by=operator_name,
                outcome="correct",
            )
            self.store.mark_lease_done(session["id"], product.bcode)
            self._enqueue_mirror(
                bcode=product.bcode,
                operator_id=operator_id,
                operator_name=operator_name,
                outcome="correct",
                variance=0.0,
                source=source,
                billno=None,
            )
            self._record_work(
                session,
                "count_correct",
                bcode=product.bcode,
                draft_id=draft_id,
                variance=0.0,
                source=source,
            )
            return {"ok": True, "status": "completed", "draft_id": draft_id, "variance": 0.0}

        draft_id = self.store.create_draft(
            {
                "bcode": product.bcode,
                "descr": product.descr,
                "location1": product.location1,
                "location2": product.location2,
                "system_qty": system_qty,
                "counted_qty": counted,
                "variance": variance,
                "entry_mode": entry_mode,
                "source": source,
                "status": "pending",
                "operator_line_user_id": operator_id,
                "operator_name": operator_name,
                "notes": notes,
                "completed_at": None,
            }
        )
        self.store.mark_lease_done(session["id"], product.bcode)
        self._record_work(
            session,
            "count_variance",
            bcode=product.bcode,
            draft_id=draft_id,
            variance=variance,
            source=source,
        )
        return {
            "ok": True,
            "status": "pending",
            "draft_id": draft_id,
            "variance": variance,
            "system_qty": system_qty,
            "counted_qty": counted,
        }

    def edit_pending_draft(
        self,
        *,
        draft_id: str,
        session: dict[str, Any],
        counted_qty: float | None = None,
        difference: float | None = None,
        notes: str | None = None,
    ) -> dict[str, Any]:
        draft = self.store.get_draft(draft_id)
        if not draft:
            raise ValueError("draft not found")
        if draft["status"] != "pending":
            raise ValueError("draft not pending")
        if self._line_id(session) != str(draft.get("operator_line_user_id") or "").strip():
            raise PermissionError("only owner can edit draft")

        product = get_product_by_bcode(draft["bcode"])
        if not product:
            raise ValueError("product not found")

        live_qty = float(product.qtyoh2)
        if difference is not None:
            counted = live_qty + float(difference)
        elif counted_qty is not None:
            counted = float(counted_qty)
        else:
            raise ValueError("provide counted_qty or difference")

        variance = counted - live_qty
        edit_count = int(draft.get("edit_count") or 0) + 1
        self.store.update_draft(
            draft_id,
            counted_qty=counted,
            variance=variance,
            system_qty=live_qty,
            notes=notes if notes is not None else draft.get("notes"),
            edit_count=edit_count,
        )
        self._record_work(
            session,
            "count_edit",
            bcode=draft["bcode"],
            draft_id=draft_id,
            variance=variance,
            source=draft.get("source"),
        )
        return {
            "ok": True,
            "draft_id": draft_id,
            "counted_qty": counted,
            "variance": variance,
            "system_qty": live_qty,
        }

    def drift_review(self, draft_id: str) -> dict[str, Any]:
        draft = self.store.get_draft(draft_id)
        if not draft:
            raise ValueError("draft not found")
        if draft["status"] != "pending":
            raise ValueError("draft not pending")

        product = get_product_by_bcode(draft["bcode"])
        if not product:
            raise ValueError("product not found")

        draft = dict(draft)
        if product.model:
            draft["model"] = product.model

        live_qty = float(product.qtyoh2)
        expected_system = float(draft["system_qty"])
        counted = float(draft["counted_qty"])
        drift = live_qty - expected_system
        new_variance = counted - live_qty

        since = datetime.fromtimestamp(float(draft["created_at"]), tz=BANGKOK)
        movements = list_stock_movements(draft["bcode"], since=since)
        explained = sum(m.qty_delta for m in movements)
        drift_gap = drift - explained

        return {
            "draft": draft,
            "product": product.as_dict(),
            "draft_system_qty": expected_system,
            "live_qty": live_qty,
            "counted_qty": counted,
            "drift": drift,
            "new_variance": new_variance,
            "movements": [
                {
                    "billno": m.billno,
                    "billdate": m.billdate.isoformat(),
                    "billtime": m.billtime,
                    "kind_label": m.kind_label,
                    "qty_delta": m.qty_delta,
                }
                for m in movements
            ],
            "explained_delta": explained,
            "unexplained_delta": drift_gap,
            "drift_fully_explained": abs(drift_gap) < 1e-6 if movements else False,
        }

    def skip_item(self, session_id: str, bcode: str) -> None:
        self.store.release_one_lease(session_id, bcode)
        self.bump_leases(session_id)

    def approve_draft(
        self,
        *,
        draft_id: str,
        approver_session: dict[str, Any],
        confirm_drift: bool = False,
    ) -> dict[str, Any]:
        draft = self.store.get_draft(draft_id)
        if not draft:
            raise ValueError("draft not found")
        if draft["status"] != "pending":
            raise ValueError(f"draft status is {draft['status']}")
        self._assert_can_approve(draft, approver_session)

        product = get_product_by_bcode(draft["bcode"])
        if not product:
            raise ValueError("product not found")

        live_qty = float(product.qtyoh2)
        expected_system = float(draft["system_qty"])
        if abs(live_qty - expected_system) > 1e-6 and not confirm_drift:
            return {
                "ok": False,
                "code": "qty_drift",
                "message": "system qty changed since count",
                "draft_id": draft_id,
                "draft_system_qty": expected_system,
                "live_qty": live_qty,
                "variance": float(draft["variance"]),
            }

        counted = float(draft["counted_qty"])
        variance = counted - live_qty
        if abs(variance) < 1e-9:
            self.store.update_draft(
                draft_id,
                status="completed",
                variance=0.0,
                system_qty=live_qty,
                completed_at=time.time(),
                approver_line_user_id=self._line_id(approver_session),
                approver_name=approver_session["display_name"],
                post_error=None,
            )
            self.store.upsert_local_audit(
                bcode=product.bcode,
                audited_by=draft["operator_name"],
                outcome="correct",
            )
            self._enqueue_mirror(
                bcode=product.bcode,
                operator_id=draft["operator_line_user_id"],
                operator_name=draft["operator_name"],
                outcome="correct",
                variance=0.0,
                source=draft["source"],
                billno=None,
                approver_id=self._line_id(approver_session),
                approver_name=approver_session["display_name"],
            )
            self._record_work(
                approver_session,
                "audit_approve",
                bcode=product.bcode,
                draft_id=draft_id,
                variance=0.0,
                source=draft["source"],
            )
            return {"ok": True, "status": "completed", "variance": 0.0}

        product.qtyoh2 = live_qty
        try:
            posted = post_stock_adjustment(
                settings=self.settings,
                product=product,
                variance=variance,
                operator_name=draft["operator_name"],
                approver_name=approver_session.get("display_name"),
            )
        except Parts9WriteError as exc:
            self.store.update_draft(draft_id, post_error=str(exc))
            return {"ok": False, "code": exc.code, "message": str(exc)}

        self.store.update_draft(
            draft_id,
            status="posted",
            variance=variance,
            system_qty=live_qty,
            posted_billno=posted.billno,
            completed_at=time.time(),
            approver_line_user_id=self._line_id(approver_session),
            approver_name=approver_session["display_name"],
            post_error=None,
        )
        self.store.upsert_local_audit(
            bcode=product.bcode,
            audited_by=draft["operator_name"],
            outcome="adjusted",
        )
        self._enqueue_mirror(
            bcode=product.bcode,
            operator_id=draft["operator_line_user_id"],
            operator_name=draft["operator_name"],
            outcome="adjusted",
            variance=variance,
            source=draft["source"],
            billno=posted.billno,
            approver_id=self._line_id(approver_session),
            approver_name=approver_session["display_name"],
        )
        self._record_work(
            approver_session,
            "audit_approve",
            bcode=product.bcode,
            draft_id=draft_id,
            variance=variance,
            source=draft["source"],
        )
        return {
            "ok": True,
            "status": "posted",
            "billno": posted.billno,
            "variance": variance,
            "new_qtyoh2": posted.new_qtyoh2,
        }

    def reject_draft(self, *, draft_id: str, approver_session: dict[str, Any]) -> None:
        draft = self.store.get_draft(draft_id)
        if not draft or draft["status"] != "pending":
            raise ValueError("draft not pending")
        is_owner = self._line_id(approver_session) == str(draft.get("operator_line_user_id") or "").strip()
        if not is_owner:
            self._assert_can_approve(draft, approver_session)

        self.store.update_draft(
            draft_id,
            status="rejected",
            approver_line_user_id=self._line_id(approver_session),
            approver_name=approver_session["display_name"],
            completed_at=time.time(),
        )
        self._record_work(
            approver_session,
            "audit_reject",
            bcode=draft["bcode"],
            draft_id=draft_id,
            variance=float(draft.get("variance") or 0),
            source=draft.get("source"),
        )

    def work_summary_today(self, line_user_id: str) -> dict[str, int]:
        now = datetime.now(BANGKOK)
        start = now.replace(hour=0, minute=0, second=0, microsecond=0)
        since_ts = start.timestamp()
        return self.store.summarize_work_events(
            line_user_id=line_user_id,
            since_ts=since_ts,
        )

    def _enqueue_mirror(self, **payload: Any) -> None:
        body = {
            "branch": self.settings.stock_check_branch,
            **payload,
            "audited_at": time.time(),
        }
        self.store.enqueue_audit_outbox(json.dumps(body, ensure_ascii=False))
