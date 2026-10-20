"""Operator control actions — shared by the REST API and the Telegram bot
(ROADMAP.md TASK-5.4) so both surfaces hit exactly the same code path.
"""
from datetime import datetime, timezone

from sqlmodel import select

from ..models import PortfolioSnapshot, Position, SystemEvent, TradingSignal, UserSetting
from ..risk.engine import CIRCUIT_BREAKER_KEY, PAUSED_KEY, count_open_positions, get_latest_portfolio, is_paused


async def _set_flag(session, key: str, active: bool) -> None:
    row = (await session.exec(select(UserSetting).where(UserSetting.key == key))).first()
    if row:
        row.value = "true" if active else "false"
        row.updated_at = datetime.now(timezone.utc)
    else:
        session.add(UserSetting(key=key, value="true" if active else "false", is_mutable=False))
    await session.commit()


async def emergency_stop(session) -> dict:
    """/kill — must take effect in <=2s (ROADMAP TASK-5.5): cancel every
    PENDING signal synchronously here, don't wait for the next engine tick."""
    start = datetime.now(timezone.utc)
    await _set_flag(session, PAUSED_KEY, True)
    await _set_flag(session, CIRCUIT_BREAKER_KEY, True)

    pending = (await session.exec(select(TradingSignal).where(TradingSignal.status == "PENDING"))).all()
    cancelled = len(pending)
    for sig in pending:
        sig.status = "REJECTED"
    session.add(
        SystemEvent(
            event_type="EMERGENCY_STOP", severity="CRITICAL",
            message=f"Emergency stop engaged — {cancelled} pending signal(s) cancelled.",
        )
    )
    await session.commit()
    elapsed_ms = (datetime.now(timezone.utc) - start).total_seconds() * 1000
    return {"engaged": True, "cancelled_signals": cancelled, "elapsed_ms": round(elapsed_ms, 1)}


async def pause_trading(session) -> dict:
    await _set_flag(session, PAUSED_KEY, True)
    session.add(SystemEvent(event_type="TRADING_PAUSED", severity="WARNING", message="Operator paused new entries."))
    await session.commit()
    return {"paused": True}


async def resume_trading(session) -> dict:
    """Manual override — also clears the circuit breaker (RBAC_AND_TELEGRAM_ACCESS.md:
    re-opening strategy after an 8% drawdown freeze is an explicit operator action)."""
    await _set_flag(session, PAUSED_KEY, False)
    await _set_flag(session, CIRCUIT_BREAKER_KEY, False)
    session.add(SystemEvent(event_type="TRADING_RESUMED", severity="INFO", message="Operator resumed trading."))
    await session.commit()
    return {"paused": False, "circuit_breaker_active": False}


async def system_status(session) -> dict:
    portfolio = await get_latest_portfolio(session)
    open_positions = await count_open_positions(session)
    paused = await is_paused(session)
    cb_row = (await session.exec(select(UserSetting).where(UserSetting.key == CIRCUIT_BREAKER_KEY))).first()
    return {
        "equity_usd": portfolio.total_equity_usd,
        "cash_balance_usd": portfolio.cash_balance_usd,
        "open_positions_value_usd": portfolio.open_positions_value_usd,
        "open_positions_count": open_positions,
        "daily_realized_pnl_usd": portfolio.daily_realized_pnl_usd,
        "daily_loss_pct": portfolio.daily_loss_pct,
        "current_drawdown_pct": portfolio.current_drawdown_pct,
        "high_water_mark_usd": portfolio.high_water_mark_usd,
        "paused": paused,
        "circuit_breaker_active": bool(cb_row and cb_row.value == "true"),
    }
