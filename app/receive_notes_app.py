"""Standalone receive-notes HTTP app (:8797)."""

from __future__ import annotations

import logging

from fastapi import FastAPI
from fastapi.responses import RedirectResponse

from app.routers.receive_notes import router as receive_notes_router

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s | %(levelname)s | %(name)s | %(message)s",
)

app = FastAPI(title="KCW Receive Notes", docs_url="/docs", redoc_url=None)
app.include_router(receive_notes_router)


@app.get("/")
def root():
    return RedirectResponse(url="/receive-notes/", status_code=307)


@app.get("/health")
def health():
    return {"status": "ok", "service": "receive-notes"}
