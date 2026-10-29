"""Copy-trading signal generator — BR-01, COPY_TRADING_FLOWCHART.mmd.

Translates on-chain DEX swaps from approved wallets into TradingSignal candidates
for the 9-gate Risk Engine, enforcing token contract safety and liquidity thresholds.
"""
from datetime import datetime, timedelta, timezone
from decimal import Decimal
import logging
from uuid import UUID

from sqlalchemy.ext.asyncio import AsyncSession
from sqlmodel import select

from ..models import AgentRun, SystemEvent, Token, TradingSignal, Wallet

logger = logging.getLogger("agents.copy_trade")

MIN_POOL_LIQUIDITY_USD = Decimal("20000.00")
MONITORED_STATUSES = ("APPROVED", "ACTIVE_MONITORED")


def validate_copy_trade_preconditions(
    wallet: Wallet, token: Token, action: str, price_usd: Decimal
) -> tuple[bool, str | None]:
    """Pure validation against COPY_TRADING_FLOWCHART.mmd decision nodes."""
    if wallet.status not in MONITORED_STATUSES:
        return False, "WALLET_NOT_MONITORED"

    act = (action or "").upper()
    # Spot paper trading is long-only: a master SELL is an exit, never a new entry. A SELL signal used
    # to be opened as a long by the broker (F-27).
    # shortcut: master SELLs are ignored and our positions exit on their own SL/TP; upgrade by closing
    # open positions on that token (COPY_TRADING_FLOWCHART.mmd SELL branch).
    if act == "SELL":
        return False, "SELL_NOT_MIRRORED"
    if act != "BUY":
        return False, "IGNORED_ACTION"

    if price_usd <= Decimal(0):
        return False, "INVALID_PRICE"

    # Token Safety Gate: freeze & mint authority must be revoked
    if not token.freeze_authority_revoked or not token.mint_authority_revoked:
        return False, "TOKEN_UNSAFE_AUTHORITY_NOT_REVOKED"

    # Liquidity Gate: pool liquidity must be >= $20,000 USD
    liquidity = token.pool_liquidity_usd or Decimal(0)
    if liquidity < MIN_POOL_LIQUIDITY_USD:
        return False, "INSUFFICIENT_POOL_LIQUIDITY"

    return True, None


async def create_copy_trade_signal(
    session: AsyncSession,
    wallet: Wallet,
    token: Token,
    action: str,
    price_usd: Decimal,
) -> TradingSignal | None:
    """Creates a TradingSignal from an approved wallet swap, routing it to the Risk Gate."""
    is_valid, reason = validate_copy_trade_preconditions(wallet, token, action, price_usd)
    if not is_valid:
        logger.info("Copy-trade rejected for wallet %s on %s: %s", wallet.address, token.symbol, reason)
        session.add(
            SystemEvent(
                event_type="COPY_TRADE_REJECTED",
                severity="INFO",
                message=f"Copy-trade from {wallet.address[:8]}... on {token.symbol} rejected: {reason}",
            )
        )
        await session.commit()
        return None

    # Record agent run
    run = AgentRun(
        agent_name="COPY_TRADE",
        task_type="WALLET_MIRROR",
        status="SUCCESS",
        execution_time_ms=Decimal("1.00"),
    )
    session.add(run)
    await session.commit()
    await session.refresh(run)

    act = "BUY"  # validate_copy_trade_preconditions only lets BUYs through
    stop_loss = (price_usd * Decimal("0.95")).quantize(Decimal("0.000001"))
    tp1 = (price_usd * Decimal("1.075")).quantize(Decimal("0.000001"))
    tp2 = (price_usd * Decimal("1.15")).quantize(Decimal("0.000001"))

    # Confidence derived from wallet score (0-100 -> 0.50-0.99)
    wallet_score = wallet.composite_score or Decimal(70)
    conf = min(Decimal("0.99"), max(Decimal("0.50"), (wallet_score / Decimal(100)).quantize(Decimal("0.001"))))
    winrate = wallet.win_rate_pct if (wallet.win_rate_pct and wallet.win_rate_pct > 0) else Decimal("60.00")

    signal = TradingSignal(
        agent_run_id=run.id,
        token_id=token.id,
        symbol=f"{token.symbol}USDT" if not token.symbol.endswith("USDT") else token.symbol,
        action=act,
        target_entry_price=price_usd,
        suggested_stop_loss=stop_loss,
        suggested_take_profit_1=tp1,
        suggested_take_profit_2=tp2,
        recommended_allocation_pct=Decimal("0.0050"),
        confidence_score=conf,
        estimated_winrate_pct=winrate,
        rationale=f"Copy-trade mirrored from approved wallet {wallet.address[:10]}... (score: {wallet_score})",
        status="PENDING",
        expires_at=datetime.now(timezone.utc) + timedelta(minutes=5),
    )
    session.add(signal)
    await session.commit()
    await session.refresh(signal)

    logger.info("Created copy-trade signal %s for %s %s from wallet %s", signal.id, act, signal.symbol, wallet.address)
    return signal
