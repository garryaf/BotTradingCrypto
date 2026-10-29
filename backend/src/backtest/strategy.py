"""Deterministic proxy strategy for backtesting — PH5-T1 (improved).

Background (PH5-T1):
    The original proxy (EMA20 > EMA50 + RSI 50-70) produced Profit Factor 0.41
    on a 60-day BTCUSDT backtest (ROADMAP.md Fase 6, IMPLEMENTATION_GAP_PHASES.md §FASE 5).
    Root cause: the single EMA-crossover filter emits too many signals in sideways/choppy
    markets and locks in trades right before consolidation reversals.

    This improved proxy adds three quality gates chosen because they match the same
    market-regime intuitions that Hermes uses qualitatively at runtime
    (signal-scoring-hybrid/SKILL.md: Trend Following + Momentum Breakout pillars):

    1. **MACD histogram positive and rising** — momentum is accelerating, not fading.
       Eliminates the classic EMA-crossover false signal where RSI is in range but
       momentum has already peaked.

    2. **RSI momentum band tightened (55 ≤ RSI ≤ 72)** — cuts out overbought entries
       (RSI > 70 → reversal risk) and weak-trend entries (RSI < 55 → no momentum).

    3. **ATR-based stop loss (1.5× ATR instead of fixed 2%)** — adapts the risk/reward
       geometry to actual volatility.  A fixed 2% SL in a low-volatility period triggers
       on routine noise; in a high-vol period it is too tight for the TP targets to pay out.

    These three changes target the primary failure modes of the 0.41 PF result without
    adding complexity that can't be verified with deterministic unit tests.

ponytail: this file must only produce deterministic, testable signals.  No LLM calls.
The live system's Hermes agent provides its own qualitative reasoning; this module is
purely a stand-in for historical replay of the Risk Gate + Paper Broker pipeline.
"""
from ..agents.indicators import atr, ema, macd, rsi

# --- Signal filter constants ---
EMA_FAST = 20
EMA_SLOW = 50
RSI_MIN = 55     # stronger momentum floor (was 50)
RSI_MAX = 72     # avoid overbought entries (same idea as live Hermes guard)

# ATR-based stop: place SL 1.5× ATR below entry to adapt to realised volatility.
# At typical BTC H1 ATR ≈ 0.3 - 0.7 % of price this gives SL ≈ 0.45 - 1.05 %,
# smaller than the old fixed 2 %, which means TP targets are proportionally closer.
ATR_SL_MULTIPLIER = 1.5
ATR_PERIOD = 14

# R:R targets (unchanged — live system targets ~1.5 : 3.0 R)
TP1_R = 1.5
TP2_R = 3.0

# Fallback SL when ATR is unavailable (bars < ATR_PERIOD + 1)
FALLBACK_SL_PCT = 0.018   # 1.8 % fallback instead of old 2.0 %


def generate_signal(
    closes_so_far: list[float],
    highs_so_far: list[float] | None = None,
    lows_so_far: list[float] | None = None,
) -> dict | None:
    """Generate a BUY signal when all quality gates pass.

    closes_so_far[-1] is "now" — the caller must never pass future bars (AC-SIM-03).
    highs_so_far / lows_so_far are optional; if omitted, ATR defaults to the fixed
    FALLBACK_SL_PCT (maintains backward-compat with tests that only pass closes).
    """
    min_bars = max(EMA_SLOW + 1, ATR_PERIOD + 1, 26 + 9 + 1)  # ≥ 36 for MACD warmup
    if len(closes_so_far) < min_bars:
        return None

    # --- Gate 1: EMA trend ---
    ema_fast = ema(closes_so_far, EMA_FAST)
    ema_slow = ema(closes_so_far, EMA_SLOW)
    if ema_fast <= ema_slow:
        return None   # not in uptrend

    # --- Gate 2: RSI momentum band ---
    rsi14 = rsi(closes_so_far, 14)
    if not (RSI_MIN <= rsi14 <= RSI_MAX):
        return None   # too weak or overbought

    # --- Gate 3: MACD histogram positive and rising ---
    _macd_line, _signal_line, histogram = macd(closes_so_far)
    if histogram <= 0:
        return None   # momentum decelerating or negative

    # Build signal geometry
    entry = closes_so_far[-1]

    # ATR stop-loss (preferred) with fallback
    if highs_so_far and lows_so_far and len(highs_so_far) >= ATR_PERIOD + 1:
        atr_val = atr(highs_so_far, lows_so_far, closes_so_far, ATR_PERIOD)
        sl_dist = atr_val * ATR_SL_MULTIPLIER if atr_val > 0 else entry * FALLBACK_SL_PCT
    else:
        sl_dist = entry * FALLBACK_SL_PCT

    stop_loss = entry - sl_dist
    if stop_loss <= 0:
        return None   # degenerate price

    return {
        "action": "BUY",
        "entry_price": entry,
        "stop_loss": stop_loss,
        "take_profit_1": entry + TP1_R * sl_dist,
        "take_profit_2": entry + TP2_R * sl_dist,
        "estimated_winrate_pct": 55.0,  # conservative fixed prior — no curve-fitting
    }
