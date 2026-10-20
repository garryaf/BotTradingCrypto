"""Equity ledger bookkeeping — DATA_MODEL.md principle #5 (double-entry
balancing): total_equity_usd must always equal cash + open positions value,
with zero drift. ROADMAP Milestone 4: "tanpa kebocoran deviasi kas vs ekuitas."
"""
from decimal import Decimal


def assert_ledger_integrity(total_equity_usd: Decimal, cash_balance_usd: Decimal, open_positions_value_usd: Decimal) -> None:
    drift = abs(total_equity_usd - (cash_balance_usd + open_positions_value_usd))
    if drift > Decimal("0.01"):
        raise AssertionError(f"ledger drift detected: equity != cash + positions (delta={drift})")


def next_snapshot(
    *,
    cash_balance_usd: Decimal,
    open_positions_value_usd: Decimal,
    high_water_mark_usd: Decimal,
    daily_realized_pnl_usd: Decimal,
) -> dict:
    total_equity_usd = cash_balance_usd + open_positions_value_usd
    assert_ledger_integrity(total_equity_usd, cash_balance_usd, open_positions_value_usd)

    hwm = max(high_water_mark_usd, total_equity_usd)
    drawdown_pct = ((hwm - total_equity_usd) / hwm * 100) if hwm > 0 else Decimal(0)
    daily_loss_pct = max(Decimal(0), -daily_realized_pnl_usd) / total_equity_usd * 100 if total_equity_usd > 0 else Decimal(0)

    return {
        "total_equity_usd": total_equity_usd,
        "cash_balance_usd": cash_balance_usd,
        "open_positions_value_usd": open_positions_value_usd,
        "daily_realized_pnl_usd": daily_realized_pnl_usd,
        "daily_loss_pct": daily_loss_pct,
        "high_water_mark_usd": hwm,
        "current_drawdown_pct": drawdown_pct,
    }
