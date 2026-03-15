from fastapi import FastAPI
from pydantic import BaseModel

from src.db import get_engine
from src.queries import query_product_by_bcode
from src.ai import format_product_answer

app = FastAPI(title="KCW API")

engine = get_engine()


class AskRequest(BaseModel):
    message: str


@app.get("/health")
def health():
    return {"status": "ok"}


@app.post("/ask")
def ask(req: AskRequest):
    bcode = req.message.strip()

    df = query_product_by_bcode(engine, bcode)

    rows = df.fillna("").to_dict(orient="records")

    formatted = format_product_answer(bcode, rows)

    return {
        "status": "ok",
        "reply": formatted
    }