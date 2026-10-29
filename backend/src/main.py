import asyncio
import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy import text

from .agents.hermes import run_hermes_loop
from .agents.wallet_scorer import run_wallet_scoring_loop
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

logger = logging.getLogger("main")

# Background loops, kept so /health can say which are still alive (GAP-14): a loop that dies
# silently stops ingestion or stop-loss monitoring while the API keeps answering "ok".
_tasks: list[asyncio.Task] = []


def _task_state(task: asyncio.Task) -> str:
    """running | exited (returned on its own, e.g. idle because unconfigured) | crashed | cancelled."""
    if not task.done():
        return "running"
    if task.cancelled():
        return "cancelled"
    return "crashed" if task.exception() else "exited"


def _log_crash(task: asyncio.Task) -> None:
    if not task.cancelled() and task.exception():
        logger.error("background loop %s crashed", task.get_name(), exc_info=task.exception())


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

    loops = {
        "binance_ingestion": run_binance_ingestion,
        "solana_ingestion": run_solana_ingestion,
        "aggregator": run_aggregator,
        "hermes": run_hermes_loop,
        "wallet_scoring": run_wallet_scoring_loop,
        "risk_engine": run_risk_engine_loop,
        "telegram_bot": run_telegram_bot,
    }
    for name, loop in loops.items():
        task = asyncio.create_task(loop(), name=name)
        task.add_done_callback(_log_crash)
        _tasks.append(task)
    yield
    # Graceful shutdown: cancel then await so each loop's `async with` (DB session,
    # httpx client) actually closes instead of being dropped mid-flight (GAP-16).
    for task in _tasks:
        task.cancel()
    await asyncio.gather(*_tasks, return_exceptions=True)
    _tasks.clear()


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
    tasks = {task.get_name(): _task_state(task) for task in _tasks}
    degraded = db_status != "connected" or "crashed" in tasks.values()
    return {
        "status": "degraded" if degraded else "ok",
        "db": db_status,
        "env": settings.app_env,
        "live_trading": settings.live_trading_enabled,
        "tasks": tasks,
    }
