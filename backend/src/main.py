import asyncio
from contextlib import asynccontextmanager

from fastapi import FastAPI
from sqlalchemy import text

from .agents.hermes import run_hermes_loop
from .db import engine
from .ingestion.aggregator import run_aggregator
from .ingestion.binance import run_binance_ingestion
from .ingestion.solana import run_solana_ingestion


@asynccontextmanager
async def lifespan(_: FastAPI):
    tasks = [
        asyncio.create_task(run_binance_ingestion()),
        asyncio.create_task(run_solana_ingestion()),
        asyncio.create_task(run_aggregator()),
        asyncio.create_task(run_hermes_loop()),
    ]
    yield
    for task in tasks:
        task.cancel()


app = FastAPI(title="AUTO-TRADE-AA Backend", lifespan=lifespan)


@app.get("/api/v1/health")
async def health() -> dict:
    try:
        async with engine.connect() as conn:
            await conn.execute(text("SELECT 1"))
        db_status = "connected"
    except Exception:
        db_status = "disconnected"
    return {"status": "ok", "db": db_status}
