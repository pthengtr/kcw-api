"""Standalone HQ vendor goods-receipt HTTP app (:8795)."""

from __future__ import annotations

import logging

from fastapi import FastAPI
from fastapi.responses import RedirectResponse

from app.routers.hq_receive import router as hq_receive_router

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s | %(levelname)s | %(name)s | %(message)s",
)

app = FastAPI(title="KCW HQ Receive", docs_url="/docs", redoc_url=None)
app.include_router(hq_receive_router)


@app.get("/")
def root():
    return RedirectResponse(url="/hq-receive/", status_code=307)


@app.get("/health")
def health():
    return {"status": "ok", "service": "kcw-hq-receive"}
