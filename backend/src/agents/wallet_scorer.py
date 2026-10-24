"""Wallet scoring engine — FR-WLT-01, BR-01, WALLET_DISCOVERY_FLOWCHART.mmd.

Calculates quantitative performance metrics from on-chain DEX observations:
- Net Realized PnL (deducting network gas & protocol fees)
- Win Rate (%)
- Profit Factor (gross_profit / abs(gross_loss))
- Max Drawdown (%)
- Composite Score (0.00 - 100.00)

Promotes discovered wallets with composite_score >= 70.00 to PENDING_REVIEW.
"""
from datetime import datetime, timezone
from decimal import Decimal, ROUND_HALF_UP
import logging

from sqlalchemy.ext.asyncio import AsyncSession
from sqlmodel import select

from ..models import Wallet, WalletObservation

logger = logging.getLogger("agents.wallet_scorer")


def calculate_wallet_metrics(observations: list[WalletObservation]) -> dict:
    """Pure deterministic calculation of wallet performance metrics."""
    if not observations:
        return {
            "total_trades": 0,
            "win_rate_pct": Decimal("0.00"),
            "profit_factor": Decimal("0.00"),
            "net_pnl_usd": Decimal("0.0000"),
            "max_drawdown_pct": Decimal("0.00"),
            "composite_score": Decimal("0.00"),
            "last_active_at": None,
        }

    # Sort observations chronologically
    sorted_obs = sorted(observations, key=lambda o: o.block_time)
    last_active_at = sorted_obs[-1].block_time

    # Pair roundtrip trades by token or calculate per-swap economics
    # Standard DEX heuristic:
    # BUY: amount_in (SOL/USD) spent to receive token_out
    # SELL: amount_in (token) sold to receive amount_out (SOL/USD)
    gross_profit = Decimal("0.00")
    gross_loss = Decimal("0.00")
    total_fee_usd = Decimal("0.00")
    wins = 0
    losses = 0

    # Token inventory tracking: token_id -> (quantity, total_cost_usd)
    inventory: dict[object, list[Decimal]] = {}  # token_id -> [qty, cost_basis]
    sol_usd_est = Decimal("150.00")  # fallback price estimate for native gas fee conversion

    for obs in sorted_obs:
        fee_usd = (obs.network_fee_native or Decimal("0.000005")) * sol_usd_est
        total_fee_usd += fee_usd

        action = (obs.action or "").upper()
        if action == "BUY" and obs.token_out_id:
            cost = obs.amount_in if obs.amount_in > 0 else (obs.amount_out * obs.price_usd if obs.price_usd > 0 else Decimal(0))
            current_qty, current_cost = inventory.get(obs.token_out_id, (Decimal(0), Decimal(0)))
            inventory[obs.token_out_id] = (current_qty + obs.amount_out, current_cost + cost)
        elif action == "SELL" and obs.token_in_id:
            proceeds = obs.amount_out if obs.amount_out > 0 else (obs.amount_in * obs.price_usd if obs.price_usd > 0 else Decimal(0))
            current_qty, current_cost = inventory.get(obs.token_in_id, (Decimal(0), Decimal(0)))
            if current_qty > 0 and obs.amount_in > 0:
                cost_share = (obs.amount_in / current_qty) * current_cost
                remaining_qty = max(Decimal(0), current_qty - obs.amount_in)
                remaining_cost = max(Decimal(0), current_cost - cost_share)
                inventory[obs.token_in_id] = (remaining_qty, remaining_cost)
            else:
                cost_share = current_cost
                inventory[obs.token_in_id] = (Decimal(0), Decimal(0))

            trade_pnl = proceeds - cost_share - fee_usd
            if trade_pnl > 0:
                wins += 1
                gross_profit += trade_pnl
            else:
                losses += 1
                gross_loss += abs(trade_pnl)
        else:
            # Transfers or standalone swaps with price_usd:
            if obs.price_usd > 0 and obs.amount_out > 0:
                trade_value = obs.amount_out * obs.price_usd
                if trade_value > fee_usd:
                    wins += 1
                    gross_profit += trade_value - fee_usd
                else:
                    losses += 1
                    gross_loss += fee_usd

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

    # Calculate Max Drawdown from cumulative PnL series
    cum_pnl = Decimal(0)
    peak = Decimal(0)
    max_dd = Decimal(0)
    for obs in sorted_obs:
        # Approximate step PnL
        step_pnl = (obs.amount_out * obs.price_usd) if obs.price_usd > 0 else Decimal(0)
        cum_pnl += step_pnl
        if cum_pnl > peak:
            peak = cum_pnl
        if peak > 0:
            dd = ((peak - cum_pnl) / peak) * Decimal(100)
            if dd > max_dd:
                max_dd = dd

    max_drawdown_pct = min(Decimal("100.00"), max_dd.quantize(Decimal("0.01"), rounding=ROUND_HALF_UP))

    # Composite Score formula (0 to 100):
    # Score = 0.35 * WinRate + 0.35 * min(100, (PF / 3) * 100) + 0.30 * max(0, 100 - (MDD * 2))
    score_wr = win_rate * Decimal("0.35")
    score_pf = min(Decimal(100), (profit_factor / Decimal(3)) * Decimal(100)) * Decimal("0.35")
    score_mdd = max(Decimal(0), Decimal(100) - (max_drawdown_pct * Decimal(2))) * Decimal("0.30")
    raw_score = score_wr + score_pf + score_mdd
    composite_score = min(Decimal("100.00"), max(Decimal("0.00"), raw_score)).quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)

    return {
        "total_trades": total_closed,
        "win_rate_pct": win_rate,
        "profit_factor": profit_factor,
        "net_pnl_usd": net_pnl,
        "max_drawdown_pct": max_drawdown_pct,
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
            wallet.status = "PENDING_REVIEW"
            logger.info("Promoted wallet %s to PENDING_REVIEW (score: %s)", wallet.address, wallet.composite_score)

        session.add(wallet)
        updated_count += 1

    if updated_count > 0:
        await session.commit()

    return updated_count
