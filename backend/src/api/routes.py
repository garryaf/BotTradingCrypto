"""REST API for the Web Dashboard — ROADMAP.md TASK-5.2/5.3."""
from decimal import Decimal

from fastapi import APIRouter, Depends
from sqlmodel import select
from sqlmodel.ext.asyncio.session import AsyncSession

from ..backtest.data import fetch_historical_bars
from ..backtest.engine import run_backtest
from ..db import get_session
from ..models import PortfolioSnapshot, Position, RiskCheck, TradingSignal
from . import control as control_actions

router = APIRouter(prefix="/api/v1")


@router.get("/portfolio")
async def get_portfolio(session: AsyncSession = Depends(get_session)):
    history = (
        await session.exec(select(PortfolioSnapshot).order_by(PortfolioSnapshot.snapshot_time.desc()).limit(200))
    ).all()
    if not history:
        return {"connected": False}
    latest = history[0]
    return {
        "connected": True,
        "equity_usd": latest.total_equity_usd,
        "cash_balance_usd": latest.cash_balance_usd,
        "open_positions_value_usd": latest.open_positions_value_usd,
        "daily_realized_pnl_usd": latest.daily_realized_pnl_usd,
        "daily_loss_pct": latest.daily_loss_pct,
        "current_drawdown_pct": latest.current_drawdown_pct,
        "high_water_mark_usd": latest.high_water_mark_usd,
        "win_rate_pct": latest.win_rate_pct,
        "profit_factor": latest.profit_factor,
        "history": [
            {"time": s.snapshot_time, "equity": s.total_equity_usd} for s in reversed(history)
        ],
    }


@router.get("/positions")
async def get_positions(session: AsyncSession = Depends(get_session)):
    rows = (await session.exec(select(Position).order_by(Position.opened_at.desc()).limit(50))).all()
    return [
        {
            "id": str(p.id),
            "symbol": p.symbol,
            "status": p.status,
            "quantity": p.current_quantity,
            "average_entry_price": p.average_entry_price,
            "current_stop_loss": p.current_stop_loss,
            "take_profit_1": p.take_profit_1,
            "take_profit_2": p.take_profit_2,
            "is_tp1_hit": p.is_tp1_hit,
            "realized_pnl_usd": p.realized_pnl_usd,
            "unrealized_pnl_usd": p.unrealized_pnl_usd,
            "opened_at": p.opened_at,
            "closed_at": p.closed_at,
        }
        for p in rows
    ]


@router.get("/signals")
async def get_signals(session: AsyncSession = Depends(get_session)):
    rows = (await session.exec(select(TradingSignal).order_by(TradingSignal.generated_at.desc()).limit(30))).all()
    return [
        {
            "symbol": s.symbol,
            "action": s.action,
            "status": s.status,
            "confidence_score": s.confidence_score,
            "estimated_winrate_pct": s.estimated_winrate_pct,
            "rationale": s.rationale,
            "generated_at": s.generated_at,
        }
        for s in rows
    ]


@router.get("/risk/status")
async def get_risk_status(session: AsyncSession = Depends(get_session)):
    latest_check = (await session.exec(select(RiskCheck).order_by(RiskCheck.evaluated_at.desc()))).first()
    status = await control_actions.system_status(session)
    gates = None
    if latest_check:
        gates = {
            "expectancy_check": latest_check.expectancy_check,
            "risk_per_trade_check": latest_check.risk_per_trade_check,
            "daily_loss_check": latest_check.daily_loss_check,
            "drawdown_check": latest_check.drawdown_check,
            "spread_check": latest_check.spread_check,
            "stop_loss_check": latest_check.stop_loss_check,
            "balance_lot_check": latest_check.balance_lot_check,
            "max_positions_check": latest_check.max_positions_check,
            "circuit_breaker_check": latest_check.circuit_breaker_check,
            "data_freshness_check": latest_check.data_freshness_check,
            "passed": latest_check.passed,
            "rejection_reasons": latest_check.rejection_reasons,
            "evaluated_at": latest_check.evaluated_at,
        }
    return {**status, "latest_check": gates}


@router.post("/control/kill")
async def control_kill(session: AsyncSession = Depends(get_session)):
    return await control_actions.emergency_stop(session)


@router.post("/control/pause")
async def control_pause(session: AsyncSession = Depends(get_session)):
    return await control_actions.pause_trading(session)


@router.post("/control/resume")
async def control_resume(session: AsyncSession = Depends(get_session)):
    return await control_actions.resume_trading(session)


@router.get("/control/status")
async def control_status(session: AsyncSession = Depends(get_session)):
    return await control_actions.system_status(session)


@router.get("/backtest/run")
async def backtest_run(symbol: str = "BTCUSDT", days: int = 60, interval: str = "1h"):
    """ROADMAP.md TASK-6.1/6.2 — on-demand, not persisted (no backtest table in DATA_DICTIONARY.md)."""
    bars = await fetch_historical_bars(symbol, interval=interval, days=days)
    report = run_backtest(bars, initial_capital=Decimal(10000))
    return {"symbol": symbol, "interval": interval, "requested_days": days, **report}
