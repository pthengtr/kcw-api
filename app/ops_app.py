"""Standalone kcw-ops (live PARTS9 PO). Parallel to cloud kcw-v2."""

from __future__ import annotations

import logging

from fastapi import FastAPI
from fastapi.responses import RedirectResponse

from app.routers.ops import router as ops_router

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s | %(levelname)s | %(name)s | %(message)s",
)

app = FastAPI(title="KCW Ops", docs_url="/docs", redoc_url=None)
app.include_router(ops_router)


@app.get("/")
def root():
    return RedirectResponse(url="/ops/", status_code=307)


@app.get("/health")
def health():
    return {"status": "ok", "service": "kcw-ops"}
