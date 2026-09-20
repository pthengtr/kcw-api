from fastapi import APIRouter, BackgroundTasks, Request

from src.tiger_pay.service import process_tiger_pay_webhook

router = APIRouter(prefix="/webhooks", tags=["webhooks"])


@router.post("/tiger-pay")
async def tiger_pay_webhook(request: Request, background_tasks: BackgroundTasks):
    return await process_tiger_pay_webhook(request, background_tasks)
