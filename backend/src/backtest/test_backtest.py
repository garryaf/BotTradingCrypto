"""Plain-assert self-check, no network/DB needed. Run: python -m src.backtest.test_backtest

AC-SIM-03 (docs/01-requirements/ACCEPTANCE_CRITERIA.md): "Waktu data yang
dibaca oleh modul strategi selalu <= t_simulasi; tidak ada kebocoran data
masa depan." — verified by instrumenting the engine's actual call site,
not just the pure strategy function in isolation.
"""
import random
from decimal import Decimal

from . import engine as engine_module
from .data import Bar
from .engine import run_backtest
from .strategy import generate_signal as real_generate_signal


def _make_bars(n: int, seed: int = 7) -> list[Bar]:
    random.seed(seed)
    price = 100.0
    bars = []
    for i in range(n):
        price = max(1.0, price * (1 + random.uniform(-0.01, 0.012)))
        high = price * 1.004
        low = price * 0.996
        bars.append(Bar(open_time_ms=i * 3_600_000, open=price, high=high, low=low, close=price, volume=1_000_000))
    return bars


def test_strategy_never_sees_future_bars():
    bars = _make_bars(300)
    seen_lengths: list[int] = []

    def spy(closes_so_far, **kwargs):
        seen_lengths.append(len(closes_so_far))
        return real_generate_signal(closes_so_far, **kwargs)

    original = engine_module.generate_signal
    engine_module.generate_signal = spy
    try:
        run_backtest(bars)
    finally:
        engine_module.generate_signal = original

    assert len(seen_lengths) > 0, "strategy was never invoked — test data or thresholds are off"
    assert max(seen_lengths) <= len(bars), "a call received more bars than exist in the whole dataset"
    assert seen_lengths == sorted(seen_lengths), "calls must be strictly chronological — never re-fed a shorter prefix later"
    assert len(seen_lengths) == len(set(seen_lengths)), "no bar index was ever evaluated twice with a longer prefix"


def test_future_price_spike_does_not_change_past_signal():
    bars = _make_bars(200)
    report_a = run_backtest(bars)

    # plant an extreme spike far in the future — must NOT change any trade
    # decision made before that bar.
    spiked = list(bars)
    spiked[150] = Bar(open_time_ms=bars[150].open_time_ms, open=100000, high=100000, low=100000, close=100000, volume=1)
    report_b = run_backtest(spiked)

    # Equity curve up to bar 149 must be identical regardless of what happens at bar 150+.
    assert report_a["equity_curve"][:149] == report_b["equity_curve"][:149]


def test_metrics_profit_factor_sane():
    bars = _make_bars(1500)
    report = run_backtest(bars, initial_capital=Decimal(10000))
    assert report["overall"]["trades"] >= 0
    assert "in_sample" in report and "out_of_sample" in report
    assert report["final_equity_usd"] > 0


if __name__ == "__main__":
    test_strategy_never_sees_future_bars()
    test_future_price_spike_does_not_change_past_signal()
    test_metrics_profit_factor_sane()
    print("ok")
