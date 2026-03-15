from fastapi import FastAPI
from pydantic import BaseModel

from src.db import get_engine
from src.queries import query_product_by_bcode

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

    return {
        "status": "ok",
        "query": bcode,
        "count": len(df),
        "rows": df.fillna("").to_dict(orient="records"),
    }