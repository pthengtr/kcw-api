from fastapi import FastAPI
from pydantic import BaseModel

app = FastAPI(title="KCW API")

class AskRequest(BaseModel):
    message: str

@app.get("/health")
def health():
    return {"status": "ok"}

@app.post("/ask")
def ask(req: AskRequest):
    return {
        "status": "ok",
        "received": req.message
    }