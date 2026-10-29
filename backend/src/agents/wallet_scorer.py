"""Wallet scoring engine — FR-WLT-01, FR-WLT-02, BR-01, WALLET_DISCOVERY_FLOWCHART.mmd.

Calculates quantitative performance metrics from on-chain DEX observations:
- Net Realized PnL in SOL (net of network gas & pool fees; stored in the historically named net_pnl_usd)
- Win Rate (%)
- Profit Factor (gross_profit / abs(gross_loss))
- Max Drawdown (%)
- Composite Score (0.00 - 100.00)

Promotes discovered wallets with composite_score >= 70.00 to PENDING_REVIEW *only* if
they pass the anti-manipulation screen (FR-WLT-02).  Wallets that fail the screen are
ARCHIVED to prevent wash-trading and 1-hit-wonder exploits from entering copy-trading.
"""
from datetime import datetime, timezone
from decimal import Decimal, ROUND_HALF_UP
import logging

from sqlalchemy.ext.asyncio import AsyncSession
from sqlmodel import select

import asyncio

from ..db import async_session_factory
from ..models import Wallet, WalletObservation
from .anti_manipulation import screen_wallet

logger = logging.getLogger("agents.wallet_scorer")

SCORING_INTERVAL_SEC = 300


def calculate_wallet_metrics(observations: list[WalletObservation]) -> dict:
    """Pure deterministic calculation of wallet performance metrics."""
    if not observations:
        return {
            "total_trades": 0,
            "win_rate_pct": Decimal("0.00"),
            "profit_factor": Decimal("0.00"),
            "net_pnl_usd": Decimal("0.0000"),
            "max_drawdown_pct": Decimal("0.00"),
            "avg_holding_time_hours": Decimal("0.00"),
            "history_days": Decimal("0.00"),
            "has_min_history_30d": False,
            "composite_score": Decimal("0.00"),
            "last_active_at": None,
        }

    sorted_obs = sorted(observations, key=lambda o: o.block_time)
    last_active_at = sorted_obs[-1].block_time

    # Units are SOL (F-29): amounts are the wallet's SOL balance deltas (ingestion/solana.py: BUY amount_in =
    # SOL spent, SELL amount_out = SOL received), which already include the network fee it paid and the pool
    # fee (FR-WLT-01). Subtracting the fee again, converted at a fixed $150, double-counted it in USD.
    # shortcut: a leg paid or received in another token (e.g. USDC) counts as 0 SOL; upgrade by pricing that leg.
    gross_profit = Decimal("0.00")
    gross_loss = Decimal("0.00")
    wins = 0
    losses = 0
    # FIFO inventory: token_id -> list of (remaining_qty, lot_cost, buy_time)
    inventory: dict[object, list[tuple[Decimal, Decimal, datetime]]] = {}
    cash = min_cash = Decimal(0)  # running SOL flow of the observed trades
    realized_curve: list[Decimal] = []  # net realized PnL after each closed trade
    holding_durations: list[tuple[float, Decimal]] = []  # (duration_seconds, qty)

    for obs in sorted_obs:
        action = (obs.action or "").upper()
        if action == "BUY" and obs.token_out_id:
            lots = inventory.setdefault(obs.token_out_id, [])
            lots.append((obs.amount_out, obs.amount_in, obs.block_time))
            cash -= obs.amount_in
            min_cash = min(min_cash, cash)
        elif action == "SELL" and obs.token_in_id:
            lots = inventory.get(obs.token_in_id, [])
            total_avail = sum(lot_qty for lot_qty, _, _ in lots)
            if total_avail <= 0 or obs.amount_in <= 0:
                continue  # bought before the observed history: unknown cost, it used to score as a 100% win

            sell_remaining = obs.amount_in
            cost_share = Decimal(0)
            new_lots: list[tuple[Decimal, Decimal, datetime]] = []

            for lot_qty, lot_cost, lot_buy_time in lots:
                if sell_remaining <= 0:
                    new_lots.append((lot_qty, lot_cost, lot_buy_time))
                    continue
                match_qty = min(lot_qty, sell_remaining)
                unit_cost = (lot_cost / lot_qty) if lot_qty > 0 else Decimal(0)
                lot_cost_share = match_qty * unit_cost
                cost_share += lot_cost_share

                if obs.block_time and lot_buy_time:
                    dur_sec = max(0.0, (obs.block_time - lot_buy_time).total_seconds())
                    holding_durations.append((dur_sec, match_qty))

                remaining_in_lot = lot_qty - match_qty
                if remaining_in_lot > 0:
                    remaining_lot_cost = lot_cost - lot_cost_share
                    new_lots.append((remaining_in_lot, remaining_lot_cost, lot_buy_time))
                sell_remaining -= match_qty

            inventory[obs.token_in_id] = new_lots
            cash += obs.amount_out

            trade_pnl = obs.amount_out - cost_share
            if trade_pnl > 0:
                wins += 1
                gross_profit += trade_pnl
            else:
                losses += 1
                gross_loss += abs(trade_pnl)
            realized_curve.append(gross_profit - gross_loss)

    total_closed = wins + losses
    if total_closed > 0:
        win_rate = (Decimal(wins) / Decimal(total_closed) * Decimal(100)).quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)
    else:
        win_rate = Decimal("0.00")

    if gross_loss > 0:
        profit_factor = (gross_profit / gross_loss).quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)
    elif gross_profit > 0:
        profit_factor = Decimal("10.00")
    else:
        profit_factor = Decimal("0.00")

    net_pnl = (gross_profit - gross_loss).quantize(Decimal("0.0001"), rounding=ROUND_HALF_UP)

    # Max drawdown from the high-water mark of realized equity (TESTING_PLAN §5.5). The old series summed
    # trade values, which never fall, so drawdown was always 0 (F-29). The wallet's capital is unknown: use
    # the least SOL that could have funded the observed trades (the deepest point of the SOL flow).
    capital = -min_cash
    peak = capital
    max_dd = Decimal(0)
    for pnl in realized_curve:
        equity = capital + pnl
        peak = max(peak, equity)
        if peak > 0:
            max_dd = max(max_dd, (peak - equity) / peak * Decimal(100))

    max_drawdown_pct = min(Decimal("100.00"), max_dd.quantize(Decimal("0.01"), rounding=ROUND_HALF_UP))

    # Composite Score formula (0 to 100):
    # Score = 0.35 * WinRate + 0.35 * min(100, (PF / 3) * 100) + 0.30 * max(0, 100 - (MDD * 2))
    score_wr = win_rate * Decimal("0.35")
    score_pf = min(Decimal(100), (profit_factor / Decimal(3)) * Decimal(100)) * Decimal("0.35")
    # No closed trade is no evidence: it must not earn the drawdown points.
    score_mdd = max(Decimal(0), Decimal(100) - (max_drawdown_pct * Decimal(2))) * Decimal("0.30") if total_closed else Decimal(0)
    raw_score = score_wr + score_pf + score_mdd
    composite_score = min(Decimal("100.00"), max(Decimal("0.00"), raw_score)).quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)

    # Average holding duration (hours) and history window (days) — FR-WLT-01
    if holding_durations:
        total_sec = sum(dur * float(qty) for dur, qty in holding_durations)
        total_qty = sum(float(qty) for _, qty in holding_durations)
        avg_holding_time_hours = Decimal(str(round(total_sec / total_qty / 3600.0, 2))) if total_qty > 0 else Decimal("0.00")
    else:
        avg_holding_time_hours = Decimal("0.00")

    if sorted_obs:
        history_seconds = max(0.0, (sorted_obs[-1].block_time - sorted_obs[0].block_time).total_seconds())
        history_days = Decimal(str(round(history_seconds / 86400.0, 2)))
    else:
        history_days = Decimal("0.00")
    has_min_history_30d = history_days >= Decimal("30.00")

    return {
        "total_trades": total_closed,
        "win_rate_pct": win_rate,
        "profit_factor": profit_factor,
        "net_pnl_usd": net_pnl,
        "max_drawdown_pct": max_drawdown_pct,
        "avg_holding_time_hours": avg_holding_time_hours,
        "history_days": history_days,
        "has_min_history_30d": has_min_history_30d,
        "composite_score": composite_score,
        "last_active_at": last_active_at,
    }


async def update_wallet_scores(session: AsyncSession) -> int:
    """Updates composite scores and metrics for all wallets that have observations."""
    wallets = (await session.exec(select(Wallet))).all()
    updated_count = 0

    for wallet in wallets:
        observations = (
            await session.exec(
                select(WalletObservation)
                .where(WalletObservation.wallet_id == wallet.id)
                .order_by(WalletObservation.block_time.asc())
            )
        ).all()

        if not observations:
            continue

        metrics = calculate_wallet_metrics(observations)
        wallet.win_rate_pct = metrics["win_rate_pct"]
        wallet.profit_factor = metrics["profit_factor"]
        wallet.net_pnl_usd = metrics["net_pnl_usd"]
        wallet.max_drawdown_pct = metrics["max_drawdown_pct"]
        wallet.composite_score = metrics["composite_score"]
        if metrics["last_active_at"]:
            wallet.last_active_at = metrics["last_active_at"]
        wallet.updated_at = datetime.now(timezone.utc)

        # FR-WLT-03 & WALLET_DISCOVERY_FLOWCHART.mmd: auto-promote to PENDING_REVIEW if score >= 70.00
        if wallet.composite_score >= Decimal("70.00") and wallet.status == "DISCOVERED":
            # FR-WLT-02: run anti-manipulation screen before promoting
            flags = screen_wallet(list(observations), metrics)
            if flags.is_clean:
                wallet.status = "PENDING_REVIEW"
                logger.info(
                    "Promoted wallet %s to PENDING_REVIEW (score: %s)",
                    wallet.address, wallet.composite_score,
                )
            else:
                wallet.status = "ARCHIVED"
                logger.warning(
                    "Wallet %s ARCHIVED (manipulation detected, score: %s): %s",
                    wallet.address, wallet.composite_score, " | ".join(flags.reasons),
                )

        session.add(wallet)
        updated_count += 1

    if updated_count > 0:
        await session.commit()

    return updated_count


async def run_wallet_scoring_loop() -> None:
    """Periodic re-scoring so DISCOVERED wallets with observations get promoted
    to PENDING_REVIEW (FR-WLT-03). Without this loop copy-trade never activates."""
    while True:
        async with async_session_factory() as session:
            try:
                await update_wallet_scores(session)
            except Exception:
                logger.exception("wallet scoring cycle failed")
        await asyncio.sleep(SCORING_INTERVAL_SEC)
