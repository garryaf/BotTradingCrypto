"""Deterministic proxy for Hermes's Trend Following pillar, for backtesting.

ponytail: the live system scores signals via an LLM (Fase 3), which isn't
reproducible/affordable to call per historical bar. This implements just the
"Trend Following" pillar from signal-scoring-hybrid/SKILL.md (EMA20>EMA50 +
RSI 50-70) as a stand-in — enough to exercise the Risk Gate + Paper Broker
honestly, not a claim that it reproduces the AI's judgement historically.
"""
from ..agents.indicators import ema, rsi

SL_PCT = 0.02  # 2% stop distance approximates the live system's ATR-based stop
TP1_R = 1.5
TP2_R = 3.0


def generate_signal(closes_so_far: list[float]) -> dict | None:
    """closes_so_far[-1] is "now" — the caller must never pass future bars."""
    if len(closes_so_far) < 51:
        return None
    ema20, ema50 = ema(closes_so_far, 20), ema(closes_so_far, 50)
    rsi14 = rsi(closes_so_far, 14)
    if not (ema20 > ema50 and 50 <= rsi14 <= 70):
        return None

    entry = closes_so_far[-1]
    stop_loss = entry * (1 - SL_PCT)
    risk_unit = entry - stop_loss
    return {
        "action": "BUY",
        "entry_price": entry,
        "stop_loss": stop_loss,
        "take_profit_1": entry + TP1_R * risk_unit,
        "take_profit_2": entry + TP2_R * risk_unit,
        "estimated_winrate_pct": 55.0,  # conservative fixed prior, no historical fitting
    }
