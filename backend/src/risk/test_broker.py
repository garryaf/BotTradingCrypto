"""Plain-assert self-check for the Paper Broker + ledger invariant.
Run: python -m src.risk.test_broker
"""
from decimal import Decimal

from .broker import SLIPPAGE_FLOOR_PCT, fee_for_venue, simulate_fills
from .ledger import assert_ledger_integrity, next_snapshot


def test_small_order_single_fill_at_floor_slippage():
    fills = simulate_fills(
        action="BUY", quantity=Decimal("0.01"), bid=Decimal("99.99"), ask=Decimal("100.01"),
        volume_24h_usd=Decimal(50_000_000),
    )
    assert len(fills) == 1
    assert fills[0]["slippage_pct"] >= SLIPPAGE_FLOOR_PCT
    assert fills[0]["price"] > Decimal(100)  # BUY fills worse than mid


def test_large_order_splits_into_two_fills():
    fills = simulate_fills(
        action="BUY", quantity=Decimal(1000), bid=Decimal("99.99"), ask=Decimal("100.01"),
        volume_24h_usd=Decimal(10_000),  # tiny volume -> order is huge relative to it
    )
    assert len(fills) == 2
    assert sum(f["quantity"] for f in fills) == Decimal(1000)
    assert fills[1]["slippage_pct"] > fills[0]["slippage_pct"]  # second slice is worse


def test_sell_fills_below_mid():
    fills = simulate_fills(
        action="SELL", quantity=Decimal("0.01"), bid=Decimal("99.99"), ask=Decimal("100.01"),
        volume_24h_usd=Decimal(50_000_000),
    )
    assert fills[0]["price"] < Decimal(100)


def test_binance_fee_vs_solana_gas():
    fee_usd, gas = fee_for_venue(Decimal(1000), "Binance_SPOT_SIM", Decimal("0.0010"))
    assert fee_usd == Decimal("1.0000")
    assert gas == 0

    fee_usd2, gas2 = fee_for_venue(Decimal(1000), "SOLANA_DEX_SIM", Decimal("0.0010"))
    assert fee_usd2 == 0
    assert gas2 > 0


def test_ledger_rejects_drift():
    try:
        assert_ledger_integrity(Decimal(100), Decimal(50), Decimal(40))  # 100 != 90
        raised = False
    except AssertionError:
        raised = True
    assert raised


def test_next_snapshot_tracks_hwm_and_drawdown():
    snap = next_snapshot(
        cash_balance_usd=Decimal(9000), open_positions_value_usd=Decimal(500),
        high_water_mark_usd=Decimal(10000), daily_realized_pnl_usd=Decimal(-200),
    )
    assert snap["total_equity_usd"] == Decimal(9500)
    assert snap["high_water_mark_usd"] == Decimal(10000)  # unchanged, below HWM
    assert snap["current_drawdown_pct"] == Decimal(5)  # (10000-9500)/10000*100


if __name__ == "__main__":
    test_small_order_single_fill_at_floor_slippage()
    test_large_order_splits_into_two_fills()
    test_sell_fills_below_mid()
    test_binance_fee_vs_solana_gas()
    test_ledger_rejects_drift()
    test_next_snapshot_tracks_hwm_and_drawdown()
    print("ok")
