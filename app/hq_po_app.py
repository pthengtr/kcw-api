"""Standalone HQ purchase-order HTTP app (:8793)."""

from __future__ import annotations

import logging

from fastapi import FastAPI
from fastapi.responses import RedirectResponse

from app.routers.hq_po import router as hq_po_router

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s | %(levelname)s | %(name)s | %(message)s",
)

app = FastAPI(title="KCW HQ PO", docs_url="/docs", redoc_url=None)
app.include_router(hq_po_router)


@app.get("/")
def root():
    return RedirectResponse(url="/hq-po/", status_code=307)


@app.get("/health")
def health():
    return {"status": "ok", "service": "kcw-hq-po"}
