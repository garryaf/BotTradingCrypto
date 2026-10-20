"""Paper Broker Matching Engine — ROADMAP.md TASK-4.2.

ponytail: no real L2 orderbook depth is ingested (Fase 2 only stores best
bid/ask + 24h volume), so partial-fill is a volume-ratio heuristic, not a
true depth walk. Upgrade when Binance diff-depth ingestion exists.
"""
from decimal import Decimal

SLIPPAGE_FLOOR_PCT = Decimal("0.0005")  # 0.05% floor, per ROADMAP TASK-4.2
LARGE_ORDER_NOTIONAL_RATIO = Decimal("0.001")  # >0.1% of 24h volume -> split the fill
SOLANA_GAS_FEE_NATIVE = Decimal("0.000005")


def _slippage_pct(spread_pct: Decimal, notional_usd: Decimal, volume_24h_usd: Decimal) -> Decimal:
    size_impact = (notional_usd / volume_24h_usd) if volume_24h_usd > 0 else Decimal("0.01")
    return max(SLIPPAGE_FLOOR_PCT, spread_pct / 2 + size_impact)


def simulate_fills(
    *, action: str, quantity: Decimal, bid: Decimal, ask: Decimal, volume_24h_usd: Decimal
) -> list[dict]:
    """Returns one or two fill slices: [{quantity, price, slippage_pct}, ...]."""
    mid = (bid + ask) / 2
    spread_pct = (ask - bid) / mid if mid else Decimal(0)
    notional = quantity * mid
    direction = 1 if action == "BUY" else -1

    # Depth-walk approximation: impact is driven by the TOTAL order's size
    # relative to 24h volume (not each slice's own, smaller size) — a later
    # slice is filled deeper in the book, so it gets an added depth penalty.
    base_impact = _slippage_pct(spread_pct, notional, volume_24h_usd)

    def _fill(qty: Decimal, depth_penalty: Decimal = Decimal(0)) -> dict:
        slip = base_impact + depth_penalty
        price = mid * (1 + direction * slip)
        return {"quantity": qty, "price": price, "slippage_pct": slip}

    if volume_24h_usd > 0 and notional / volume_24h_usd > LARGE_ORDER_NOTIONAL_RATIO:
        first_qty = quantity * Decimal("0.7")
        second_qty = quantity - first_qty
        return [_fill(first_qty), _fill(second_qty, depth_penalty=Decimal("0.0003"))]
    return [_fill(quantity)]


def fee_for_venue(notional_usd: Decimal, venue: str, taker_fee_pct: Decimal) -> tuple[Decimal, Decimal]:
    """Returns (fee_usd, gas_fee_native)."""
    if venue == "SOLANA_DEX_SIM":
        return Decimal(0), SOLANA_GAS_FEE_NATIVE
    return notional_usd * taker_fee_pct, Decimal(0)
