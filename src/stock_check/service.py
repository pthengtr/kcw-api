from __future__ import annotations

import json
import time
from typing import Any

from src.stock_check.config import StockCheckSettings, get_stock_check_settings
from src.stock_check.daily_pick import pick_daily_products
from src.stock_check.db_local import LocalStore
from src.stock_check.parts9 import (
    get_product_by_bcode,
    lookup_products,
)
from src.stock_check.sa_writer import Parts9WriteError, post_stock_adjustment


class StockCheckService:
    def __init__(
        self,
        settings: StockCheckSettings | None = None,
        store: LocalStore | None = None,
    ):
        self.settings = settings or get_stock_check_settings()
        self.store = store or LocalStore(self.settings.sqlite_path)

    def expire(self) -> None:
        self.store.expire_stale_leases()

    def take_n(self, session_id: str, count: int, *, with_stock_only: bool = True) -> list[dict[str, Any]]:
        """Lease next SKUs using weighted everyday ABC / risk groups.

        ``with_stock_only`` is kept for API compatibility; negative-stock
        anomalies are always eligible (override). Active leases and pending
        drafts are excluded; returned SKUs are claim_lease'd for this session.
        Idle TTL starts now and is refreshed by count activity / heartbeat.
        """
        del with_stock_only  # daily rules decide stock filters
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
        # Keep any prior unfinished leases alive while taking more.
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
        """Refresh idle timer for this session's active leases."""
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
        # Keep take order (leased_at), not location sort — location walk is in picker.
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
        return card

    def lookup(self, query: str) -> list[dict[str, Any]]:
        products = lookup_products(query)
        audits = self.store.get_local_audits([p.bcode for p in products])
        held = self.store.active_leased_bcodes()
        out = []
        for product in products:
            card = self._product_card(product, audits.get(product.bcode))
            card["leased_elsewhere"] = product.bcode in held
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
        operator_id = session["line_user_id"]
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
        return {
            "ok": True,
            "status": "pending",
            "draft_id": draft_id,
            "variance": variance,
            "system_qty": system_qty,
            "counted_qty": counted,
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
        if not approver_session.get("is_approver"):
            raise PermissionError("approver role required")
        draft = self.store.get_draft(draft_id)
        if not draft:
            raise ValueError("draft not found")
        if draft["status"] != "pending":
            raise ValueError(f"draft status is {draft['status']}")

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
                "draft_system_qty": expected_system,
                "live_qty": live_qty,
                "variance": float(draft["variance"]),
            }

        # Recompute variance against live qty using counted qty
        counted = float(draft["counted_qty"])
        variance = counted - live_qty
        if abs(variance) < 1e-9:
            self.store.update_draft(
                draft_id,
                status="completed",
                variance=0.0,
                system_qty=live_qty,
                completed_at=time.time(),
                approver_line_user_id=approver_session["line_user_id"],
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
                approver_id=approver_session["line_user_id"],
                approver_name=approver_session["display_name"],
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
            approver_line_user_id=approver_session["line_user_id"],
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
            approver_id=approver_session["line_user_id"],
            approver_name=approver_session["display_name"],
        )
        return {
            "ok": True,
            "status": "posted",
            "billno": posted.billno,
            "variance": variance,
            "new_qtyoh2": posted.new_qtyoh2,
        }

    def reject_draft(self, *, draft_id: str, approver_session: dict[str, Any]) -> None:
        if not approver_session.get("is_approver"):
            raise PermissionError("approver role required")
        draft = self.store.get_draft(draft_id)
        if not draft or draft["status"] != "pending":
            raise ValueError("draft not pending")
        self.store.update_draft(
            draft_id,
            status="rejected",
            approver_line_user_id=approver_session["line_user_id"],
            approver_name=approver_session["display_name"],
            completed_at=time.time(),
        )

    def _enqueue_mirror(self, **payload: Any) -> None:
        body = {
            "branch": self.settings.stock_check_branch,
            **payload,
            "audited_at": time.time(),
        }
        self.store.enqueue_audit_outbox(json.dumps(body, ensure_ascii=False))
