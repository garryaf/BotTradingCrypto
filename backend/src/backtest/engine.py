"""Backtest engine — ROADMAP.md TASK-6.1/6.2.

Reuses the exact same Risk Gate / Paper Broker / Ledger functions as live
trading (Fase 4) so the simulation honestly reflects production rules.

AC-SIM-03 (docs/01-requirements/ACCEPTANCE_CRITERIA.md): the strategy is
only ever shown closes[:i+1] when deciding bar i — never a future close.
is_stale/snapshot_time are forced "fresh" here because that gate guards a
*live* feed going stale, which has no meaning for a historical replay.
"""
from datetime import datetime, timezone
from decimal import Decimal

from ..risk.broker import fee_for_venue, simulate_fills
from ..risk.gate import BINANCE_TAKER_FEE_PCT, evaluate_risk
from .data import Bar
from .strategy import generate_signal

MIN_LOT_SIZE = Decimal("0.0001")


def _day_of(open_time_ms: int):
    return datetime.fromtimestamp(open_time_ms / 1000, tz=timezone.utc).date()


def _metrics(trades: list[dict]) -> dict:
    if not trades:
        return {"trades": 0, "win_rate_pct": 0.0, "profit_factor": 0.0, "net_pnl_usd": 0.0}
    wins = [t["pnl"] for t in trades if t["pnl"] > 0]
    losses = [t["pnl"] for t in trades if t["pnl"] <= 0]
    gross_profit = sum(wins)
    gross_loss = abs(sum(losses))
    return {
        "trades": len(trades),
        "win_rate_pct": round(len(wins) / len(trades) * 100, 2),
        "profit_factor": round(gross_profit / gross_loss, 4) if gross_loss > 0 else float("inf"),
        "net_pnl_usd": round(sum(t["pnl"] for t in trades), 4),
    }


def run_backtest(bars: list[Bar], initial_capital: Decimal = Decimal(10000)) -> dict:
    closes = [b.close for b in bars]
    split_idx = int(len(bars) * 0.7)  # TASK-6.2: 70% in-sample / 30% out-of-sample, chronological

    cash = initial_capital
    hwm = initial_capital
    position: dict | None = None
    daily_pnl = Decimal(0)
    current_day = None
    circuit_breaker_active = False
    trades: list[dict] = []
    equity_curve: list[float] = []
    max_drawdown_pct = Decimal(0)

    for i, bar in enumerate(bars):
        day = _day_of(bar.open_time_ms)
        if day != current_day:
            daily_pnl = Decimal(0)
            current_day = day
            circuit_breaker_active = False  # daily-loss freeze clears on a new day; drawdown freeze persists below

        price = Decimal(str(bar.close))
        high, low = Decimal(str(bar.high)), Decimal(str(bar.low))

        if position is not None:
            if not position["is_tp1_hit"] and high >= position["take_profit_1"]:
                close_qty = position["quantity"] / 2
                exit_price = position["take_profit_1"]
                proceeds = close_qty * exit_price
                fee_usd, _ = fee_for_venue(proceeds, "Binance_SPOT_SIM", BINANCE_TAKER_FEE_PCT)
                pnl = proceeds - fee_usd - (close_qty * position["entry_price"])
                cash += proceeds - fee_usd
                position["quantity"] -= close_qty
                position["is_tp1_hit"] = True
                position["current_stop_loss"] = position["entry_price"]
                daily_pnl += pnl
                trades.append({"pnl": float(pnl), "entry_idx": position["entry_idx"]})
            elif low <= position["current_stop_loss"] or high >= position["take_profit_2"]:
                exit_price = position["current_stop_loss"] if low <= position["current_stop_loss"] else position["take_profit_2"]
                proceeds = position["quantity"] * exit_price
                fee_usd, _ = fee_for_venue(proceeds, "Binance_SPOT_SIM", BINANCE_TAKER_FEE_PCT)
                pnl = proceeds - fee_usd - (position["quantity"] * position["entry_price"])
                cash += proceeds - fee_usd
                daily_pnl += pnl
                trades.append({"pnl": float(pnl), "entry_idx": position["entry_idx"]})
                position = None

        if position is None:
            signal = generate_signal(closes[: i + 1])  # AC-SIM-03: strictly no future bars
            if signal:
                equity = cash
                hwm = max(hwm, equity)
                drawdown_pct = ((hwm - equity) / hwm * 100) if hwm > 0 else Decimal(0)
                max_drawdown_pct = max(max_drawdown_pct, drawdown_pct)
                daily_loss_pct = (max(Decimal(0), -daily_pnl) / equity * 100) if equity > 0 else Decimal(0)
                volume_24h_usd = Decimal(str(sum(b.volume * b.close for b in bars[max(0, i - 24) : i + 1])))

                if drawdown_pct >= 8:
                    circuit_breaker_active = True

                outcome = evaluate_risk(
                    action=signal["action"],
                    entry_price=Decimal(str(signal["entry_price"])),
                    stop_loss=Decimal(str(signal["stop_loss"])),
                    take_profit_1=Decimal(str(signal["take_profit_1"])),
                    take_profit_2=Decimal(str(signal["take_profit_2"])),
                    estimated_winrate_pct=Decimal(str(signal["estimated_winrate_pct"])),
                    equity_usd=equity,
                    cash_balance_usd=cash,
                    daily_loss_pct=daily_loss_pct,
                    current_drawdown_pct=drawdown_pct,
                    spread_pct=Decimal("0.01"),
                    volume_24h_usd=volume_24h_usd,
                    snapshot_time=datetime.now(timezone.utc),  # see module docstring
                    is_stale=False,
                    open_positions_count=0,
                    circuit_breaker_active=circuit_breaker_active,
                    min_lot_size=MIN_LOT_SIZE,
                )
                if outcome.passed:
                    fills = simulate_fills(
                        action="BUY", quantity=outcome.quantity, bid=price, ask=price, volume_24h_usd=volume_24h_usd
                    )
                    qty = sum(f["quantity"] for f in fills)
                    notional = sum(f["quantity"] * f["price"] for f in fills)
                    fee_usd, _ = fee_for_venue(notional, "Binance_SPOT_SIM", BINANCE_TAKER_FEE_PCT)
                    cash -= notional + fee_usd
                    position = {
                        "quantity": qty,
                        "entry_price": notional / qty,
                        "current_stop_loss": Decimal(str(signal["stop_loss"])),
                        "take_profit_1": Decimal(str(signal["take_profit_1"])),
                        "take_profit_2": Decimal(str(signal["take_profit_2"])),
                        "is_tp1_hit": False,
                        "entry_idx": i,
                    }

        mark_to_market = cash + (position["quantity"] * price if position else Decimal(0))
        equity_curve.append(float(mark_to_market))

    in_sample_trades = [t for t in trades if t["entry_idx"] < split_idx]
    out_sample_trades = [t for t in trades if t["entry_idx"] >= split_idx]

    return {
        "bars": len(bars),
        "final_equity_usd": equity_curve[-1] if equity_curve else float(initial_capital),
        "max_drawdown_pct": round(float(max_drawdown_pct), 2),
        "in_sample": _metrics(in_sample_trades),
        "out_of_sample": _metrics(out_sample_trades),
        "overall": _metrics(trades),
        "equity_curve": equity_curve,
    }
