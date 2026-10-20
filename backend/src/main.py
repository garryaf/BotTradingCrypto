from fastapi import FastAPI
from sqlalchemy import text

from .db import engine

app = FastAPI(title="AUTO-TRADE-AA Backend")


@app.get("/api/v1/health")
async def health() -> dict:
    try:
        async with engine.connect() as conn:
            await conn.execute(text("SELECT 1"))
        db_status = "connected"
    except Exception:
        db_status = "disconnected"
    return {"status": "ok", "db": db_status}
