"""Risk Gate + Paper Broker orchestration loop — ROADMAP.md TASK-4.1-4.4.

Pipeline per cycle: expire stale PENDING signals -> fan each remaining
PENDING signal out to every linked account (evaluate_risk() with THAT
account's own portfolio numbers) -> on pass, simulate_fills() and open a
position for that account -> mark-to-market / TP1 / TP2 / SL every open
position, grouped by account -> refresh that account's own circuit breaker
from its own latest portfolio snapshot.

A TradingSignal is shared market analysis (see agents/hermes.py), not an
account-owned row — it has no single pass/fail outcome once multiple
accounts can each accept or reject it on their own numbers. Its `status`
only tracks whether it's still awaiting dispatch; each account's actual
outcome lives on their own RiskCheck.passed.

Ledger convention: a position's recorded value is its COST BASIS while
opening (so opening a trade only ever moves money cash -> positions, equity
drops by exactly the fee), and CURRENT MARK-TO-MARKET value once it is being
monitored (so floating PnL shows up before a position closes).
"""
import asyncio
import logging
from collections import defaultdict
from datetime import datetime, timezone
from decimal import Decimal
from uuid import UUID

from sqlmodel import select

from ..config import settings
from ..db import async_session_factory
from ..models import (
    BinanceCredential,
    MarketSnapshot,
    PaperOrder,
    PaperTrade,
    Position,
    PortfolioSnapshot,
    RiskCheck,
    SystemEvent,
    Token,
    TradingSignal,
    UserSetting,
)
from .broker import fee_for_venue, simulate_fills
from .gate import BINANCE_TAKER_FEE_PCT, evaluate_risk
from .ledger import next_snapshot

logger = logging.getLogger("risk.engine")

CYCLE_INTERVAL_SEC = 5

# Global, operator-wide — unchanged, still driven by api/control.py + the Telegram bot.
CIRCUIT_BREAKER_KEY = "CIRCUIT_BREAKER_ACTIVE"
PAUSED_KEY = "TRADING_PAUSED"

OPEN_POSITION_STATUSES = ["OPEN", "PARTIALLY_CLOSED"]


def _account_paused_key(user_id: UUID) -> str:
    return f"ACCOUNT_PAUSED:{user_id}"


def _account_breaker_key(user_id: UUID) -> str:
    return f"ACCOUNT_CIRCUIT_BREAKER:{user_id}"


async def _flag_is_set(session, key: str) -> bool:
    row = (await session.exec(select(UserSetting).where(UserSetting.key == key))).first()
    return bool(row and row.value == "true")


async def get_latest_portfolio(session, user_id: UUID) -> PortfolioSnapshot:
    snap = (
        await session.exec(
            select(PortfolioSnapshot)
            .where(PortfolioSnapshot.user_id == user_id)
            .order_by(PortfolioSnapshot.snapshot_time.desc())
        )
    ).first()
    if snap:
        return snap
    capital = settings.initial_paper_capital_usd
    snap = PortfolioSnapshot(
        user_id=user_id,
        total_equity_usd=capital,
        cash_balance_usd=capital,
        open_positions_value_usd=Decimal(0),
        high_water_mark_usd=capital,
    )
    session.add(snap)
    await session.commit()
    await session.refresh(snap)
    return snap


async def count_open_positions(session, user_id: UUID) -> int:
    rows = (
        await session.exec(
            select(Position).where(Position.user_id == user_id, Position.status.in_(OPEN_POSITION_STATUSES))
        )
    ).all()
    return len(rows)


async def count_all_open_positions(session) -> int:
    """Operator-level total across every account — used by the global /control/status only."""
    rows = (await session.exec(select(Position).where(Position.status.in_(OPEN_POSITION_STATUSES)))).all()
    return len(rows)


async def is_paused(session) -> bool:
    """Global operator pause — unchanged, Telegram bot + api/control.py."""
    return await _flag_is_set(session, PAUSED_KEY)


async def is_account_paused(session, user_id: UUID) -> bool:
    """True if the operator paused everyone, OR this account's own circuit breaker tripped."""
    if await is_paused(session):
        return True
    return await _flag_is_set(session, _account_paused_key(user_id)) or await _flag_is_set(
        session, _account_breaker_key(user_id)
    )


async def _set_account_circuit_breaker(session, user_id: UUID, active: bool, reason: str) -> None:
    key = _account_breaker_key(user_id)
    row = (await session.exec(select(UserSetting).where(UserSetting.key == key))).first()
    was_active = bool(row and row.value == "true")
    if row:
        row.value = "true" if active else "false"
        row.updated_at = datetime.now(timezone.utc)
    else:
        session.add(UserSetting(key=key, value="true" if active else "false", is_mutable=False))
    if active and not was_active:
        session.add(
            SystemEvent(
                event_type="ACCOUNT_CIRCUIT_BREAKER_TRIGGERED",
                severity="CRITICAL",
                message=f"[user {user_id}] {reason}",
            )
        )
    await session.commit()


async def _expire_stale_signals(session) -> None:
    now = datetime.now(timezone.utc)
    pending = (await session.exec(select(TradingSignal).where(TradingSignal.status == "PENDING"))).all()
    for sig in pending:
        if sig.expires_at <= now:
            sig.status = "EXPIRED"
    await session.commit()


def _execution_venue(chain: str) -> str:
    return "SOLANA_DEX_SIM" if chain == "solana" else "Binance_SPOT_SIM"


async def _write_snapshot(
    session, user_id: UUID, prev: PortfolioSnapshot, *, cash_balance_usd: Decimal, open_positions_value_usd: Decimal,
    realized_pnl_delta: Decimal = Decimal(0),
) -> None:
    fields = next_snapshot(
        cash_balance_usd=cash_balance_usd,
        open_positions_value_usd=open_positions_value_usd,
        high_water_mark_usd=prev.high_water_mark_usd,
        daily_realized_pnl_usd=prev.daily_realized_pnl_usd + realized_pnl_delta,
    )
    session.add(PortfolioSnapshot(user_id=user_id, **fields))
    await session.commit()

    if fields["daily_loss_pct"] >= settings.daily_loss_limit_pct * 100:
        await _set_account_circuit_breaker(session, user_id, True, f"Daily loss {fields['daily_loss_pct']:.2f}% >= limit")
    elif fields["current_drawdown_pct"] >= settings.max_drawdown_limit_pct * 100:
        await _set_account_circuit_breaker(session, user_id, True, f"Drawdown {fields['current_drawdown_pct']:.2f}% >= limit")


async def _process_signal(session, signal: TradingSignal, user_id: UUID) -> None:
    """Evaluate + (maybe) execute one shared signal against one account's own numbers.
    Never mutates signal.status — the caller owns that once it's offered to every account."""
    token = await session.get(Token, signal.token_id)
    market = (
        await session.exec(
            select(MarketSnapshot)
            .where(MarketSnapshot.token_id == token.id)
            .order_by(MarketSnapshot.snapshot_time.desc())
        )
    ).first()
    if market is None:
        return  # no market data yet for this token — leave PENDING until ingestion catches up

    portfolio = await get_latest_portfolio(session, user_id)
    circuit_breaker_active = await is_account_paused(session, user_id)
    open_positions = await count_open_positions(session, user_id)

    outcome = evaluate_risk(
        action=signal.action,
        entry_price=signal.target_entry_price,
        stop_loss=signal.suggested_stop_loss,
        take_profit_1=signal.suggested_take_profit_1,
        take_profit_2=signal.suggested_take_profit_2,
        estimated_winrate_pct=signal.estimated_winrate_pct or Decimal(50),
        equity_usd=portfolio.total_equity_usd,
        cash_balance_usd=portfolio.cash_balance_usd,
        daily_loss_pct=portfolio.daily_loss_pct,
        current_drawdown_pct=portfolio.current_drawdown_pct,
        spread_pct=market.spread_pct or Decimal(0),
        volume_24h_usd=market.volume_24h_usd or Decimal(0),
        snapshot_time=market.snapshot_time,
        is_stale=market.is_stale,
        open_positions_count=open_positions,
        circuit_breaker_active=circuit_breaker_active,
        min_lot_size=token.min_lot_size,
    )

    risk_check = RiskCheck(
        user_id=user_id,
        trading_signal_id=signal.id,
        passed=outcome.passed,
        expectancy_check=outcome.expectancy_check,
        risk_per_trade_check=outcome.risk_per_trade_check,
        daily_loss_check=outcome.daily_loss_check,
        drawdown_check=outcome.drawdown_check,
        spread_check=outcome.spread_check,
        stop_loss_check=outcome.stop_loss_check,
        balance_lot_check=outcome.balance_lot_check,
        max_positions_check=outcome.max_positions_check,
        circuit_breaker_check=outcome.circuit_breaker_check,
        data_freshness_check=outcome.data_freshness_check,
        rejection_reasons=outcome.rejection_reasons,
    )
    session.add(risk_check)
    await session.commit()
    await session.refresh(risk_check)

    if not outcome.passed:
        return

    venue = _execution_venue(token.chain)
    fills = simulate_fills(
        action=signal.action, quantity=outcome.quantity, bid=market.bid_price or market.price_usd,
        ask=market.ask_price or market.price_usd, volume_24h_usd=market.volume_24h_usd or Decimal(0),
    )
    order = PaperOrder(
        risk_check_id=risk_check.id,
        client_order_id=f"ORD-{risk_check.id}",
        symbol=signal.symbol,
        side=signal.action,
        requested_quantity=outcome.quantity,
        requested_price=signal.target_entry_price,
        calculated_dollar_risk=outcome.dollar_risk,
        status="FILLED",
    )
    session.add(order)
    await session.commit()
    await session.refresh(order)

    position = Position(
        user_id=user_id,
        token_id=token.id,
        symbol=signal.symbol,
        current_quantity=Decimal(0),
        average_entry_price=Decimal(0),
        current_stop_loss=signal.suggested_stop_loss,
        take_profit_1=signal.suggested_take_profit_1,
        take_profit_2=signal.suggested_take_profit_2,
    )
    session.add(position)
    await session.commit()
    await session.refresh(position)

    total_notional = Decimal(0)
    total_fee = Decimal(0)
    total_qty = Decimal(0)
    for fill in fills:
        notional = fill["quantity"] * fill["price"]
        fee_usd, gas_native = fee_for_venue(notional, venue, BINANCE_TAKER_FEE_PCT)
        session.add(
            PaperTrade(
                paper_order_id=order.id,
                position_id=position.id,
                executed_quantity=fill["quantity"],
                executed_price=fill["price"],
                slippage_pct=fill["slippage_pct"] * 100,
                transaction_fee_usd=fee_usd,
                gas_fee_native=gas_native,
                execution_venue=venue,
            )
        )
        total_notional += notional
        total_fee += fee_usd
        total_qty += fill["quantity"]

    position.current_quantity = total_qty
    position.average_entry_price = total_notional / total_qty if total_qty else Decimal(0)
    await session.commit()

    # Cash -> position at cost basis; the fee is the only immediate equity loss.
    await _write_snapshot(
        session, user_id, portfolio,
        cash_balance_usd=portfolio.cash_balance_usd - total_notional - total_fee,
        open_positions_value_usd=portfolio.open_positions_value_usd + total_notional,
        realized_pnl_delta=-total_fee,
    )


async def _monitor_positions(session) -> None:
    positions = (await session.exec(select(Position).where(Position.status.in_(OPEN_POSITION_STATUSES)))).all()
    if not positions:
        return

    by_user: dict[UUID, list[Position]] = defaultdict(list)
    for pos in positions:
        by_user[pos.user_id].append(pos)

    for user_id, user_positions in by_user.items():
        portfolio = await get_latest_portfolio(session, user_id)
        total_positions_value = Decimal(0)
        cash_inflow = Decimal(0)
        realized_delta = Decimal(0)

        for pos in user_positions:
            market = (
                await session.exec(
                    select(MarketSnapshot).where(MarketSnapshot.token_id == pos.token_id)
                    .order_by(MarketSnapshot.snapshot_time.desc())
                )
            ).first()
            if not market:
                total_positions_value += pos.current_quantity * pos.average_entry_price
                continue
            price = market.price_usd

            if not pos.is_tp1_hit and price >= pos.take_profit_1:
                close_qty = pos.current_quantity / 2
                proceeds = close_qty * price
                fee_usd, _ = fee_for_venue(proceeds, "Binance_SPOT_SIM", BINANCE_TAKER_FEE_PCT)
                pnl = proceeds - fee_usd - (close_qty * pos.average_entry_price)
                session.add(
                    PaperTrade(paper_order_id=pos.id, position_id=pos.id, executed_quantity=close_qty,
                               executed_price=price, transaction_fee_usd=fee_usd, execution_venue="Binance_SPOT_SIM")
                )
                pos.current_quantity -= close_qty
                pos.is_tp1_hit = True
                pos.current_stop_loss = pos.average_entry_price  # move SL to breakeven
                pos.status = "PARTIALLY_CLOSED"
                pos.realized_pnl_usd += pnl
                cash_inflow += proceeds - fee_usd
                realized_delta += pnl
            elif price >= pos.take_profit_2 or price <= pos.current_stop_loss:
                proceeds = pos.current_quantity * price
                fee_usd, _ = fee_for_venue(proceeds, "Binance_SPOT_SIM", BINANCE_TAKER_FEE_PCT)
                pnl = proceeds - fee_usd - (pos.current_quantity * pos.average_entry_price)
                session.add(
                    PaperTrade(paper_order_id=pos.id, position_id=pos.id, executed_quantity=pos.current_quantity,
                               executed_price=price, transaction_fee_usd=fee_usd, execution_venue="Binance_SPOT_SIM")
                )
                pos.realized_pnl_usd += pnl
                cash_inflow += proceeds - fee_usd
                realized_delta += pnl
                pos.current_quantity = Decimal(0)
                pos.status = "CLOSED"
                pos.closed_at = datetime.now(timezone.utc)
            else:
                pos.unrealized_pnl_usd = pos.current_quantity * (price - pos.average_entry_price)

            pos.updated_at = datetime.now(timezone.utc)
            if pos.status != "CLOSED":
                total_positions_value += pos.current_quantity * price

        await session.commit()
        await _write_snapshot(
            session, user_id, portfolio,
            cash_balance_usd=portfolio.cash_balance_usd + cash_inflow,
            open_positions_value_usd=total_positions_value,
            realized_pnl_delta=realized_delta,
        )


async def run_risk_engine_loop() -> None:
    while True:
        async with async_session_factory() as session:
            await _expire_stale_signals(session)
            if not await is_paused(session):
                user_ids = (await session.exec(select(BinanceCredential.user_id))).all()
                pending = (await session.exec(select(TradingSignal).where(TradingSignal.status == "PENDING"))).all()
                for signal in pending:
                    for user_id in user_ids:
                        if await is_account_paused(session, user_id):
                            continue
                        try:
                            await _process_signal(session, signal, user_id)
                        except Exception:
                            logger.exception("risk engine failed processing signal %s for user %s", signal.id, user_id)
                    if user_ids:
                        signal.status = "DISPATCHED"
                        await session.commit()
            try:
                await _monitor_positions(session)
            except Exception:
                logger.exception("risk engine failed monitoring positions")
        await asyncio.sleep(CYCLE_INTERVAL_SEC)
