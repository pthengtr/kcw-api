"""Standalone PARTS9 explorer (separate from Tiger Pay / stock-check)."""

from __future__ import annotations

import logging

from fastapi import FastAPI
from fastapi.responses import RedirectResponse

from app.routers.parts9_explorer import router as explorer_router

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s | %(levelname)s | %(name)s | %(message)s",
)

app = FastAPI(title="KCW PARTS9 Explorer", docs_url="/docs", redoc_url=None)
app.include_router(explorer_router)


@app.get("/")
def root():
    return RedirectResponse(url="/parts9/", status_code=307)


@app.get("/health")
def health():
    return {"status": "ok", "service": "parts9-explorer"}
