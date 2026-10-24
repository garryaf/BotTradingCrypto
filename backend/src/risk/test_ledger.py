"""Plain-assert self-check for isolated ledger compounding & High-Water Mark (FR-SIM-02).
Run: python -m src.risk.test_ledger
"""
from decimal import Decimal

from .ledger import assert_ledger_integrity, next_snapshot


def test_assert_ledger_integrity_balanced():
    # Exactly balanced: equity == cash + positions
    assert_ledger_integrity(
        total_equity_usd=Decimal("10000.00"),
        cash_balance_usd=Decimal("6000.00"),
        open_positions_value_usd=Decimal("4000.00"),
    )


def test_assert_ledger_integrity_drift_raises():
    try:
        assert_ledger_integrity(
            total_equity_usd=Decimal("10000.00"),
            cash_balance_usd=Decimal("6000.00"),
            open_positions_value_usd=Decimal("3990.00"),  # $10 drift
        )
        failed = False
    except AssertionError as e:
        failed = True
        assert "ledger drift detected" in str(e)
    assert failed, "unbalanced ledger must raise AssertionError"


def test_next_snapshot_compounding_and_hwm_progression():
    # 1. Initial snapshot: $10,000 cash, 0 positions
    snap1 = next_snapshot(
        cash_balance_usd=Decimal("10000.00"),
        open_positions_value_usd=Decimal("0.00"),
        high_water_mark_usd=Decimal("10000.00"),
        daily_realized_pnl_usd=Decimal("0.00"),
    )
    assert snap1["total_equity_usd"] == Decimal("10000.00")
    assert snap1["high_water_mark_usd"] == Decimal("10000.00")
    assert snap1["current_drawdown_pct"] == Decimal("0.00")
    assert snap1["daily_loss_pct"] == Decimal("0.00")

    # 2. Portfolio grows to $12,000 ($8k cash + $4k open positions)
    snap2 = next_snapshot(
        cash_balance_usd=Decimal("8000.00"),
        open_positions_value_usd=Decimal("4000.00"),
        high_water_mark_usd=snap1["high_water_mark_usd"],
        daily_realized_pnl_usd=Decimal("2000.00"),
    )
    assert snap2["total_equity_usd"] == Decimal("12000.00")
    assert snap2["high_water_mark_usd"] == Decimal("12000.00")
    assert snap2["current_drawdown_pct"] == Decimal("0.00")

    # 3. Portfolio draws down to $11,040 ($7,040 cash + $4,000 positions)
    # HWM should remain $12,000, and drawdown should be exactly 8.00%
    snap3 = next_snapshot(
        cash_balance_usd=Decimal("7040.00"),
        open_positions_value_usd=Decimal("4000.00"),
        high_water_mark_usd=snap2["high_water_mark_usd"],
        daily_realized_pnl_usd=Decimal("-220.80"),  # 2.0% daily loss
    )
    assert snap3["total_equity_usd"] == Decimal("11040.00")
    assert snap3["high_water_mark_usd"] == Decimal("12000.00")
    assert snap3["current_drawdown_pct"] == Decimal("8.00")
    assert snap3["daily_loss_pct"] == Decimal("2.00")


def test_next_snapshot_zero_equity_handling():
    snap = next_snapshot(
        cash_balance_usd=Decimal("0.00"),
        open_positions_value_usd=Decimal("0.00"),
        high_water_mark_usd=Decimal("0.00"),
        daily_realized_pnl_usd=Decimal("0.00"),
    )
    assert snap["total_equity_usd"] == Decimal("0.00")
    assert snap["high_water_mark_usd"] == Decimal("0.00")
    assert snap["current_drawdown_pct"] == Decimal("0.00")
    assert snap["daily_loss_pct"] == Decimal("0.00")


if __name__ == "__main__":
    test_assert_ledger_integrity_balanced()
    test_assert_ledger_integrity_drift_raises()
    test_next_snapshot_compounding_and_hwm_progression()
    test_next_snapshot_zero_equity_handling()
    print("ok")
