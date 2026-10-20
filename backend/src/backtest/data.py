"""Historical OHLCV fetch for backtesting — ROADMAP.md TASK-6.1 (60 hari Binance)."""
from dataclasses import dataclass

import httpx

REST_BASE = "https://data-api.binance.vision/api/v3/klines"


@dataclass
class Bar:
    open_time_ms: int
    open: float
    high: float
    low: float
    close: float
    volume: float


async def fetch_historical_bars(symbol: str, interval: str = "1h", days: int = 60) -> list[Bar]:
    """Binance limits a single request to 1000 candles — page backwards with endTime."""
    bars: list[Bar] = []
    limit = 1000
    end_time: int | None = None
    bars_per_day = {"1h": 24, "15m": 96, "1d": 1}.get(interval, 24)
    target = days * bars_per_day

    async with httpx.AsyncClient(timeout=15) as client:
        while len(bars) < target:
            params = {"symbol": symbol, "interval": interval, "limit": limit}
            if end_time:
                params["endTime"] = end_time
            res = await client.get(REST_BASE, params=params)
            res.raise_for_status()
            page = res.json()
            if not page:
                break
            batch = [
                Bar(open_time_ms=int(k[0]), open=float(k[1]), high=float(k[2]), low=float(k[3]),
                    close=float(k[4]), volume=float(k[5]))
                for k in page
            ]
            bars = batch + bars
            end_time = batch[0].open_time_ms - 1
            if len(page) < limit:
                break

    bars.sort(key=lambda b: b.open_time_ms)
    return bars[-target:] if len(bars) > target else bars
