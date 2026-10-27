"""Standalone full-invoice HTTP app (:8794)."""

from __future__ import annotations

import logging

from fastapi import FastAPI
from fastapi.responses import RedirectResponse

from app.routers.to_bill import router as to_bill_router

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s | %(levelname)s | %(name)s | %(message)s",
)

app = FastAPI(title="KCW TO bill", docs_url="/docs", redoc_url=None)
app.include_router(to_bill_router)


@app.get("/")
def root():
    return RedirectResponse(url="/to-bill/", status_code=307)


@app.get("/health")
def health():
    return {"status": "ok", "service": "kcw-to-bill"}
