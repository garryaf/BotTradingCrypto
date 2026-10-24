import asyncio
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy import text

from .agents.hermes import run_hermes_loop
from .api.admin_routes import router as admin_router
from .api.auth_routes import router as auth_router
from .api.routes import router as api_router
from .config import settings
from .control.telegram_bot import run_telegram_bot
from .db import engine
from .ingestion.aggregator import run_aggregator
from .ingestion.binance import run_binance_ingestion
from .ingestion.solana import run_solana_ingestion
from .risk.engine import run_risk_engine_loop


@asynccontextmanager
async def lifespan(_: FastAPI):
    # Enforce Layer 2 & 3 Safety Gate (Hardcoded Live Lock per LIVE_TRADING_SAFETY_GATE.md)
    from .risk.burner_guard import assert_paper_mode
    assert_paper_mode()
    if settings.live_trading_enabled is not False:
        raise RuntimeError(
            "[SAFETY GATE] LIVE_TRADING_ENABLED is hard-locked to False on Phase 0-6. "
            "Real capital execution is prohibited by safety policy."
        )
    if not settings.jwt_secret_key or not settings.field_encryption_key:
        raise RuntimeError("JWT_SECRET_KEY and FIELD_ENCRYPTION_KEY must be set (see .env.example).")

    tasks = [
        asyncio.create_task(run_binance_ingestion()),
        asyncio.create_task(run_solana_ingestion()),
        asyncio.create_task(run_aggregator()),
        asyncio.create_task(run_hermes_loop()),
        asyncio.create_task(run_risk_engine_loop()),
        asyncio.create_task(run_telegram_bot()),
    ]
    yield
    for task in tasks:
        task.cancel()


app = FastAPI(title="AUTO-TRADE-AA Backend", lifespan=lifespan)

cors_list = [origin.strip() for origin in settings.cors_origins.split(",") if origin.strip()]
app.add_middleware(
    CORSMiddleware,
    allow_origins=cors_list,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)
app.include_router(api_router)
app.include_router(auth_router)
app.include_router(admin_router)


@app.get("/api/v1/health")
async def health() -> dict:
    try:
        async with engine.connect() as conn:
            await conn.execute(text("SELECT 1"))
        db_status = "connected"
    except Exception:
        db_status = "disconnected"
    return {
        "status": "ok",
        "db": db_status,
        "env": settings.app_env,
        "live_trading": settings.live_trading_enabled,
    }
