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

import httpx
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
from .engine_client import call_risk_engine
from .gate import BINANCE_TAKER_FEE_PCT, MAX_OPEN_POSITIONS, MIN_24H_VOLUME_USD, evaluate_risk
from .ledger import next_snapshot

logger = logging.getLogger("risk.engine")

CYCLE_INTERVAL_SEC = 5

# Global, operator-wide — unchanged, still driven by api/control.py + the Telegram bot.
CIRCUIT_BREAKER_KEY = "CIRCUIT_BREAKER_ACTIVE"
PAUSED_KEY = "TRADING_PAUSED"

OPEN_POSITION_STATUSES = ["OPEN", "PARTIALLY_CLOSED"]
UNKNOWN_SPREAD_PCT = Decimal(100)  # percent; far above any max_spread_pct, so the gate fails


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
        try:
            from ..control.telegram_bot import notify_operator
            await notify_operator(f"🚨 [CIRCUIT BREAKER TRIGGERED]\nUser: {user_id}\nReason: {reason}")
        except Exception:
            pass
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


def _spread_or_fail(market: MarketSnapshot) -> Decimal:
    """A spread is only known from a bid/ask quote. DEX pool snapshots (DEXScreener) have none, and their
    spread_pct still reads 0.0000 (the column's server default fills an omitted/None value), so the spread
    gate used to pass them as zero. An unknown spread must fail the gate, in Python and in the Rust payload."""
    if market.bid_price is None or market.ask_price is None or market.spread_pct is None:
        return UNKNOWN_SPREAD_PCT
    return market.spread_pct


def risk_limits(venue: str = "Binance_SPOT_SIM") -> dict:
    """Thresholds the gates enforce, in payload units: percent for spread/loss/drawdown, fraction
    for risk/trade. Single source for the Rust engine payload and the dashboard labels."""
    is_dex = venue == "SOLANA_DEX_SIM"
    max_spread = float(settings.max_dex_spread_pct * 100) if is_dex else float(settings.max_spread_pct * 100)
    min_vol = float(settings.min_dex_24h_volume_usd) if is_dex else float(MIN_24H_VOLUME_USD)
    return {
        "max_risk_per_trade_pct": float(settings.max_risk_per_trade_pct),
        "daily_loss_limit_pct": float(settings.daily_loss_limit_pct * 100),
        "max_drawdown_limit_pct": float(settings.max_drawdown_limit_pct * 100),
        "max_spread_pct": max_spread,
        "min_24h_volume_usd": min_vol,
        "max_open_positions": MAX_OPEN_POSITIONS,
        "data_freshness_max_age_sec": settings.data_freshness_max_age_sec,
        "min_risk_reward_ratio": float(settings.min_risk_reward_ratio),
    }


def _signal_candidate(signal: TradingSignal, market: MarketSnapshot, portfolio: PortfolioSnapshot,
                      open_positions: int, outcome, venue: str = "Binance_SPOT_SIM") -> dict:
    """SignalCandidate payload — RUST_ENGINE_INTEGRATION_SPEC.md §4.1."""
    # shortcut: Decimal -> float for the JSON contract, fine for a pass/fail verdict; switch to strings if the engine ever returns money.
    return {
        "signal_id": str(signal.id),
        "symbol": signal.symbol,
        "action": signal.action,
        "target_entry_price": float(signal.target_entry_price),
        "suggested_stop_loss": float(signal.suggested_stop_loss),
        "suggested_take_profit_1": float(signal.suggested_take_profit_1),
        "suggested_take_profit_2": float(signal.suggested_take_profit_2),
        "recommended_allocation_pct": float(outcome.risk_pct_used),
        "confidence_score": float(signal.confidence_score),
        # Rust engine mirrors gate.py's fee-aware expectancy (RUST_ENGINE_INTEGRATION_SPEC parity).
        "estimated_winrate_pct": float(signal.estimated_winrate_pct or 50),
        "dollar_risk": float(outcome.dollar_risk),
        "fee_usd": float(outcome.fee_usd),
        # Single source of truth: the engine enforces THESE limits, not its own hardcoded copy.
        "limits": risk_limits(venue),
        "snapshot": {
            "price_usd": float(market.price_usd),
            "bid_price": float(market.bid_price or market.price_usd),
            "ask_price": float(market.ask_price or market.price_usd),
            "spread_pct": float(_spread_or_fail(market)),
            "snapshot_age_seconds": int((datetime.now(timezone.utc) - market.snapshot_time).total_seconds()),
            "pool_liquidity_usd": float(market.volume_24h_usd or market.pool_liquidity_usd or 0),
        },
        "portfolio": {
            "total_equity_usd": float(portfolio.total_equity_usd),
            "cash_balance_usd": float(portfolio.cash_balance_usd),
            "daily_realized_pnl_usd": float(portfolio.daily_realized_pnl_usd),
            "daily_loss_pct": float(portfolio.daily_loss_pct),
            "high_water_mark_usd": float(portfolio.high_water_mark_usd),
            "current_drawdown_pct": float(portfolio.current_drawdown_pct),
            "open_positions_count": open_positions,
        },
    }


async def _process_signal(
    session, signal: TradingSignal, user_id: UUID, client: httpx.AsyncClient | None = None
) -> bool:
    """Evaluate + (maybe) execute one shared signal against one account's own numbers.
    Returns True once this account has a verdict on the signal, False if it can't be judged yet.
    Never mutates signal.status — the caller owns that once it's offered to every account."""
    # Idempotent: one verdict (so at most one order) per account per signal, even when the signal
    # is offered again after a crash/restart that happened before it was marked DISPATCHED.
    # shortcut: app-level check, enough for the single risk loop; add a unique (user_id,
    # trading_signal_id) constraint on risk_checks if this loop ever runs in more than one process.
    already_decided = (
        await session.exec(
            select(RiskCheck.id).where(RiskCheck.trading_signal_id == signal.id, RiskCheck.user_id == user_id)
        )
    ).first()
    if already_decided:
        return True

    token = await session.get(Token, signal.token_id)
    market = (
        await session.exec(
            select(MarketSnapshot)
            .where(MarketSnapshot.token_id == token.id)
            .order_by(MarketSnapshot.snapshot_time.desc())
        )
    ).first()
    if market is None:
        return False  # no market data yet for this token — leave PENDING until ingestion catches up

    portfolio = await get_latest_portfolio(session, user_id)
    circuit_breaker_active = await is_account_paused(session, user_id)
    open_positions = await count_open_positions(session, user_id)
    venue = _execution_venue(token.chain)

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
        spread_pct=_spread_or_fail(market),
        volume_24h_usd=market.volume_24h_usd or Decimal(0),
        snapshot_time=market.snapshot_time,
        is_stale=market.is_stale,
        open_positions_count=open_positions,
        circuit_breaker_active=circuit_breaker_active,
        min_lot_size=token.min_lot_size,
        venue=venue,
    )

    # Engine verdict is ANDed with the local one: sizing stays in Python (the IPC contract returns no sizing).
    if settings.engine_url:
        engine_passed, engine_reasons = await call_risk_engine(
            _signal_candidate(signal, market, portfolio, open_positions, outcome, venue=venue), client
        )
        if not engine_passed:
            outcome.passed = False
            outcome.rejection_reasons += engine_reasons
        if "ENGINE_UNAVAILABLE" in engine_reasons:
            await _set_account_circuit_breaker(
                session, user_id, True, "Rust Risk Gate engine unreachable — trading frozen (fail-closed)"
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
        return True

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
    return True


async def _opening_order_id(session, position: Position) -> UUID | None:
    """Exit fills are booked against the order that opened the position: paper_orders.risk_check_id is
    NOT NULL, so an exit can't have an order of its own. Booking them on position.id broke the
    paper_trades FK on every TP/SL exit, so no position ever closed (F-26)."""
    return (await session.exec(select(PaperTrade.paper_order_id).where(PaperTrade.position_id == position.id))).first()


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
            order_id = await _opening_order_id(session, pos)
            if order_id is None:  # no entry fill was recorded (crash mid-execution, F-18): nothing to exit
                logger.error("position %s has no opening order; skipped", pos.id)
                continue
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

            pos_token = await session.get(Token, pos.token_id)
            venue = _execution_venue(pos_token.chain) if pos_token else "Binance_SPOT_SIM"

            if not pos.is_tp1_hit and price >= pos.take_profit_1:
                close_qty = pos.current_quantity / 2
                proceeds = close_qty * price
                fee_usd, gas_native = fee_for_venue(proceeds, venue, BINANCE_TAKER_FEE_PCT)
                pnl = proceeds - fee_usd - (close_qty * pos.average_entry_price)
                session.add(
                    PaperTrade(paper_order_id=order_id, position_id=pos.id, executed_quantity=close_qty,
                               executed_price=price, transaction_fee_usd=fee_usd, gas_fee_native=gas_native,
                               execution_venue=venue)
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
                fee_usd, gas_native = fee_for_venue(proceeds, venue, BINANCE_TAKER_FEE_PCT)
                pnl = proceeds - fee_usd - (pos.current_quantity * pos.average_entry_price)
                session.add(
                    PaperTrade(paper_order_id=order_id, position_id=pos.id, executed_quantity=pos.current_quantity,
                               executed_price=price, transaction_fee_usd=fee_usd, gas_fee_native=gas_native,
                               execution_venue=venue)
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


async def _dispatch_pending(session, client: httpx.AsyncClient | None = None) -> None:
    """Offer every PENDING signal to every unpaused account. A signal becomes DISPATCHED only once
    an account actually decided on it; with no market data it stays PENDING until it expires."""
    user_ids = (await session.exec(select(BinanceCredential.user_id))).all()
    pending = (await session.exec(select(TradingSignal).where(TradingSignal.status == "PENDING"))).all()
    for signal in pending:
        decided = False
        for user_id in user_ids:
            if await is_account_paused(session, user_id):
                continue
            try:
                decided = await _process_signal(session, signal, user_id, client) or decided
            except Exception:
                logger.exception("risk engine failed processing signal %s for user %s", signal.id, user_id)
                # A failed write leaves the session unusable: the next query would raise outside this
                # try and kill the loop. Roll back and end this round; the retry is safe (idempotent),
                # and a signal that keeps failing only blocks dispatch until it expires (5 min).
                await session.rollback()
                return
        if decided:
            signal.status = "DISPATCHED"
            await session.commit()


async def run_risk_engine_loop() -> None:
    # One pooled client so the 10ms engine budget isn't spent on a fresh TCP handshake per signal.
    async with httpx.AsyncClient() as client:
        while True:
            async with async_session_factory() as session:
                await _expire_stale_signals(session)
                if not await is_paused(session):
                    await _dispatch_pending(session, client)
                try:
                    await _monitor_positions(session)
                except Exception:
                    logger.exception("risk engine failed monitoring positions")
            await asyncio.sleep(CYCLE_INTERVAL_SEC)
