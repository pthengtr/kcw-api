"""Standalone pay-notes HTTP app (:8791)."""

from __future__ import annotations

import logging

from fastapi import FastAPI
from fastapi.responses import RedirectResponse

from app.routers.pay_notes import router as pay_notes_router

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s | %(levelname)s | %(name)s | %(message)s",
)

app = FastAPI(title="KCW Pay Notes", docs_url="/docs", redoc_url=None)
app.include_router(pay_notes_router)


@app.get("/")
def root():
    return RedirectResponse(url="/pay-notes/", status_code=307)


@app.get("/health")
def health():
    return {"status": "ok", "service": "pay-notes"}
