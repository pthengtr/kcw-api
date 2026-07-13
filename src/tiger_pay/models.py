from decimal import Decimal
from typing import Any

from pydantic import BaseModel, ConfigDict, Field


class TigerPayShop(BaseModel):
    model_config = ConfigDict(extra="allow")

    name: str | None = None
    shopName: str | None = None
    branchName: str | None = None


class TigerPayPayment(BaseModel):
    model_config = ConfigDict(extra="allow")

    id: int
    type: str
    paymentNo: str
    status: str
    amount: Decimal | int | float | str
    totalPay: Decimal | int | float | str
    createdAt: str
    updatedAt: str
    refNo1: str | None = None
    refNo2: str | None = None
    note: str | None = None
    remark: str | None = None
    change: Any = None


class TigerPayWebhookPayload(BaseModel):
    model_config = ConfigDict(extra="allow")

    payment: TigerPayPayment
    shop: TigerPayShop


class TigerPayIngestResult(BaseModel):
    event_id: int | str
    duplicate: bool
    transaction_updated: bool
