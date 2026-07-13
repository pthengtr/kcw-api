from fastapi import APIRouter, Request

from src.tiger_pay.service import process_tiger_pay_webhook

router = APIRouter(prefix="/webhooks", tags=["webhooks"])


@router.post("/tiger-pay")
async def tiger_pay_webhook(request: Request):
    return await process_tiger_pay_webhook(request)
