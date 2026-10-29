"""Anti-manipulation screening for wallet discovery — FR-WLT-02.

Detects two classes of manipulation that can inflate a wallet's composite score:

1. **Wash Trading**: rapid buy-sell cycles on the same token within a short window
   (≤ 5 minutes between BUY and subsequent SELL of the same token), especially
   with near-zero net PnL.  Signature: high trade count on a token, very low
   elapsed time between round-trip.

2. **1-Hit Wonder**: a wallet with an exceptional composite_score but whose
   entire PnL history comes from a single token or a single trade.  This pattern
   often results from a lucky pump-and-dump exit, not repeatable skill.

The result is a dataclass `ManipulationFlags` returned by
`screen_wallet(observations, metrics)`.  It is then consumed by
`wallet_scorer.py::update_wallet_scores` to mark flagged wallets
ARCHIVED instead of promoting them to PENDING_REVIEW.

Design principles (ponytail):
- Pure function — no DB access, no I/O.
- All thresholds are named constants (can be tuned without touching logic).
- Deterministic: same observations → same flags, every time.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timedelta
from decimal import Decimal

from ..models import WalletObservation

# ─── Tunable thresholds ────────────────────────────────────────────────────────

# Wash-trading: a BUY→SELL round-trip for the same token within this window is
# suspicious.  5 min is a safe lower-bound (legitimate traders rarely flip in
# under a block or two on Solana — ~0.4 s per block means 5 min ≈ 750 blocks).
WASH_WINDOW_SECONDS: int = 300  # 5 minutes

# Wash-trading: if a wallet has ≥ this many suspicious round-trips it is flagged.
WASH_MIN_SUSPICIOUS_PAIRS: int = 2

# Wash-trading: net PnL of a round-trip must be within ±this fraction of cost
# basis to be considered "zero-gain" (eliminates legitimate tight-scalp trades
# from false-positive flags).
WASH_ZERO_GAIN_THRESHOLD: Decimal = Decimal("0.01")  # ±1 %

# 1-hit wonder: if a single token contributes > this fraction of gross_profit
# the score is inflated by one lucky trade, not skill.
ONE_HIT_CONCENTRATION_THRESHOLD: Decimal = Decimal("0.80")  # 80 %

# 1-hit wonder: only flag when the wallet has fewer than this many *total*
# closed trades (a wallet with 50+ trades and 80 % concentration in one token
# might genuinely specialise in it).
ONE_HIT_MAX_TOTAL_TRADES: int = 5


# ─── Result type ───────────────────────────────────────────────────────────────

@dataclass
class ManipulationFlags:
    """Screening result.  ``is_clean`` is False when any flag is raised."""
    is_clean: bool = True

    wash_trade_detected: bool = False
    wash_suspicious_pairs: int = 0          # count of flagged round-trips

    one_hit_wonder_detected: bool = False
    one_hit_token_address: str | None = None  # address of the dominant token
    one_hit_concentration_pct: Decimal = Decimal("0.00")

    reasons: list[str] = field(default_factory=list)

    def _flag(self, reason: str) -> None:
        self.is_clean = False
        self.reasons.append(reason)


# ─── Internal helpers ──────────────────────────────────────────────────────────

def _detect_wash_trades(
    observations: list[WalletObservation],
) -> tuple[bool, int]:
    """Returns (flagged, suspicious_pair_count).

    Algorithm:
    - Group observations by the *non-SOL token* involved in each leg.
    - Within each group, walk chronologically and look for BUY→SELL pairs
      where the elapsed time ≤ WASH_WINDOW_SECONDS *and* the net PnL is
      within ±WASH_ZERO_GAIN_THRESHOLD of the cost basis.
    """
    # Build a per-token timeline of (block_time, action, amount_in, amount_out)
    # using token_out_id for BUY (the token bought) and token_in_id for SELL.
    token_events: dict[object, list[tuple[datetime, str, Decimal, Decimal]]] = {}

    for obs in sorted(observations, key=lambda o: o.block_time):
        action = (obs.action or "").upper()
        if action == "BUY" and obs.token_out_id:
            token_events.setdefault(obs.token_out_id, []).append(
                (obs.block_time, "BUY", obs.amount_in, obs.amount_out)
            )
        elif action == "SELL" and obs.token_in_id:
            token_events.setdefault(obs.token_in_id, []).append(
                (obs.block_time, "SELL", obs.amount_in, obs.amount_out)
            )

    suspicious_count = 0
    window = timedelta(seconds=WASH_WINDOW_SECONDS)

    for _token_id, events in token_events.items():
        # Simple state machine: pending_buys is a list of (time, cost_basis)
        pending_buys: list[tuple[datetime, Decimal, Decimal]] = []  # (time, qty, cost)

        for ev_time, action, amount_in, amount_out in events:
            if action == "BUY":
                pending_buys.append((ev_time, amount_out, amount_in))  # qty=amount_out, cost=amount_in
            elif action == "SELL" and pending_buys:
                buy_time, buy_qty, buy_cost = pending_buys[0]
                elapsed = ev_time - buy_time
                if elapsed <= window and buy_qty > 0:
                    # Sold portion of the pending buy
                    sell_qty = amount_in
                    cost_share = (min(sell_qty, buy_qty) / buy_qty) * buy_cost
                    proceeds = amount_out
                    if cost_share > 0:
                        net_pnl_ratio = abs(proceeds - cost_share) / cost_share
                        if net_pnl_ratio <= WASH_ZERO_GAIN_THRESHOLD:
                            suspicious_count += 1
                # Remove exhausted buys regardless of whether flagged
                remaining_qty = buy_qty - amount_in
                if remaining_qty <= 0:
                    pending_buys.pop(0)
                elif pending_buys:
                    t, _, c = pending_buys[0]
                    qty_ratio = max(Decimal(0), remaining_qty) / buy_qty if buy_qty > 0 else Decimal(0)
                    pending_buys[0] = (t, max(Decimal(0), remaining_qty), c * qty_ratio)

    flagged = suspicious_count >= WASH_MIN_SUSPICIOUS_PAIRS
    return flagged, suspicious_count


def _detect_one_hit_wonder(
    observations: list[WalletObservation],
    metrics: dict,
) -> tuple[bool, str | None, Decimal]:
    """Returns (flagged, dominant_token_id_str, concentration_pct).

    Calculates gross_profit per token and checks if one token dominates.
    Only checks wallets with few total trades (see ONE_HIT_MAX_TOTAL_TRADES).
    """
    total_trades = metrics.get("total_trades", 0)
    if total_trades == 0 or total_trades > ONE_HIT_MAX_TOTAL_TRADES:
        return False, None, Decimal("0.00")

    # Re-calculate per-token PnL contribution (mirrors logic in wallet_scorer)
    inventory: dict[object, tuple[Decimal, Decimal]] = {}  # token_id → (qty, cost)
    profit_by_token: dict[object, Decimal] = {}

    for obs in sorted(observations, key=lambda o: o.block_time):
        action = (obs.action or "").upper()
        if action == "BUY" and obs.token_out_id:
            curr_qty, curr_cost = inventory.get(obs.token_out_id, (Decimal(0), Decimal(0)))
            inventory[obs.token_out_id] = (curr_qty + obs.amount_out, curr_cost + obs.amount_in)
        elif action == "SELL" and obs.token_in_id:
            curr_qty, curr_cost = inventory.get(obs.token_in_id, (Decimal(0), Decimal(0)))
            if curr_qty <= 0 or obs.amount_in <= 0:
                continue
            cost_share = (obs.amount_in / curr_qty) * curr_cost
            trade_pnl = obs.amount_out - cost_share
            profit_by_token[obs.token_in_id] = profit_by_token.get(obs.token_in_id, Decimal(0)) + trade_pnl
            inventory[obs.token_in_id] = (
                max(Decimal(0), curr_qty - obs.amount_in),
                max(Decimal(0), curr_cost - cost_share),
            )

    total_gross_profit = sum(v for v in profit_by_token.values() if v > 0)
    if total_gross_profit <= 0:
        return False, None, Decimal("0.00")

    dominant_token_id = max(profit_by_token, key=lambda t: max(profit_by_token[t], Decimal(0)))
    dominant_profit = max(profit_by_token.get(dominant_token_id, Decimal(0)), Decimal(0))
    concentration = (dominant_profit / total_gross_profit * Decimal(100)).quantize(Decimal("0.01"))

    flagged = concentration >= ONE_HIT_CONCENTRATION_THRESHOLD * 100
    return flagged, str(dominant_token_id) if flagged else None, concentration


# ─── Public API ───────────────────────────────────────────────────────────────

def screen_wallet(
    observations: list[WalletObservation],
    metrics: dict,
) -> ManipulationFlags:
    """Run all manipulation checks and return a ManipulationFlags result.

    Args:
        observations: All WalletObservation rows for this wallet, in any order.
        metrics: The dict returned by ``calculate_wallet_metrics``.

    Returns:
        ManipulationFlags — check ``.is_clean`` before promoting the wallet.
    """
    flags = ManipulationFlags()

    # --- Check 1: Wash Trading ---
    wash_flagged, suspicious_pairs = _detect_wash_trades(observations)
    if wash_flagged:
        flags.wash_trade_detected = True
        flags.wash_suspicious_pairs = suspicious_pairs
        flags._flag(
            f"WASH_TRADE: {suspicious_pairs} suspicious round-trip(s) within "
            f"{WASH_WINDOW_SECONDS}s window with near-zero net PnL"
        )

    # --- Check 2: 1-Hit Wonder ---
    one_hit_flagged, dominant_token, concentration = _detect_one_hit_wonder(observations, metrics)
    if one_hit_flagged:
        flags.one_hit_wonder_detected = True
        flags.one_hit_token_address = dominant_token
        flags.one_hit_concentration_pct = concentration
        flags._flag(
            f"ONE_HIT_WONDER: {concentration}% of gross profit from single token "
            f"(token_id={dominant_token}) across only {metrics.get('total_trades')} trade(s)"
        )

    return flags
