"""Standalone stock-check HTTP app (separate from Tiger Pay / companion)."""

from __future__ import annotations

import logging

from fastapi import FastAPI

from app.routers.stock_check import router as stock_check_router

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s | %(levelname)s | %(name)s | %(message)s",
)

app = FastAPI(title="KCW Stock Check", docs_url="/docs", redoc_url=None)
app.include_router(stock_check_router)


@app.get("/health")
def health():
    return {"status": "ok", "service": "stock-check"}
