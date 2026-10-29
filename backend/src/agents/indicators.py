"""ponytail: EMA/RSI/MACD/ATR (stdlib, no numpy/ta-lib).

MACD and ATR added for the improved backtest proxy strategy (PH5-T1).
The LLM in live trading reasons qualitatively from market context; these
indicators capture the same signals deterministically for historical replay.
"""


def ema(values: list[float], period: int) -> float:
    period = min(period, len(values))
    k = 2 / (period + 1)
    avg = sum(values[:period]) / period
    for v in values[period:]:
        avg = v * k + avg * (1 - k)
    return avg


def rsi(values: list[float], period: int = 14) -> float:
    if len(values) < period + 1:
        return 50.0
    gains, losses = [], []
    for prev, cur in zip(values[-(period + 1) : -1], values[-period:]):
        delta = cur - prev
        gains.append(max(delta, 0))
        losses.append(max(-delta, 0))
    avg_gain, avg_loss = sum(gains) / period, sum(losses) / period
    if avg_loss == 0:
        return 100.0
    rs = avg_gain / avg_loss
    return 100 - (100 / (1 + rs))


def macd(values: list[float], fast: int = 12, slow: int = 26, signal: int = 9) -> tuple[float, float, float]:
    """Returns (macd_line, signal_line, histogram).

    Returns (0, 0, 0) when there are not enough bars to calculate.
    """
    if len(values) < slow + signal:
        return 0.0, 0.0, 0.0
    fast_ema = ema(values, fast)
    slow_ema = ema(values, slow)
    macd_line = fast_ema - slow_ema
    # Approximate signal line: EMA of MACD over the last `signal` bars
    # Build a short MACD series from the tail of values to get a proper EMA.
    macd_series = []
    for i in range(slow + signal, len(values) + 1):
        f = ema(values[:i], fast)
        s = ema(values[:i], slow)
        macd_series.append(f - s)
    if len(macd_series) < signal:
        return macd_line, macd_line, 0.0
    signal_line = ema(macd_series, signal)
    histogram = macd_line - signal_line
    return macd_line, signal_line, histogram


def atr(highs: list[float], lows: list[float], closes: list[float], period: int = 14) -> float:
    """Average True Range.  Returns 0.0 when there are not enough bars."""
    if len(closes) < period + 1 or len(highs) < period + 1 or len(lows) < period + 1:
        return 0.0
    trs = []
    h, l, c = highs[-period - 1 :], lows[-period - 1 :], closes[-period - 1 :]
    for i in range(1, len(c)):
        tr = max(h[i] - l[i], abs(h[i] - c[i - 1]), abs(l[i] - c[i - 1]))
        trs.append(tr)
    return sum(trs) / len(trs) if trs else 0.0
