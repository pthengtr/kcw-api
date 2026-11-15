"""Standalone HQ online-sale HTTP app (:8796) — TAD/CNTAD + merged TO full invoice."""

from __future__ import annotations

import logging

from fastapi import FastAPI
from fastapi.responses import RedirectResponse

from app.routers.online_sale import router as online_sale_router
from app.routers.to_bill import router as to_bill_router

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s | %(levelname)s | %(name)s | %(message)s",
)

app = FastAPI(title="KCW Online Sale", docs_url="/docs", redoc_url=None)
app.include_router(online_sale_router)
app.include_router(to_bill_router)


@app.get("/")
def root():
    return RedirectResponse(url="/online-sale/", status_code=307)


@app.get("/health")
def health():
    return {"status": "ok", "service": "kcw-online-sale", "includes": ["to-bill"]}
