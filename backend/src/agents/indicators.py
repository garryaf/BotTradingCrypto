"""ponytail: EMA/RSI only (stdlib, no numpy/ta-lib). MACD/ADX/ATR/VWAP from
market-regime-detection's full checklist are deferred — the LLM reasons
qualitatively from closes+EMA+RSI until a strategy needs the rest precisely."""


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
