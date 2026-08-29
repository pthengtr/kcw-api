"""Standalone kcw-transfer HTTP app (:8792)."""

from __future__ import annotations

import logging

from fastapi import FastAPI
from fastapi.responses import RedirectResponse

from app.routers.transfer import router as transfer_router

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s | %(levelname)s | %(name)s | %(message)s",
)

app = FastAPI(title="KCW Transfer", docs_url="/docs", redoc_url=None)
app.include_router(transfer_router)


@app.get("/")
def root():
    return RedirectResponse(url="/transfer/", status_code=307)


@app.get("/health")
def health():
    return {"status": "ok", "service": "kcw-transfer"}
