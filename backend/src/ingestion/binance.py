import asyncio
import logging
from datetime import datetime, timezone
from decimal import Decimal

import httpx
from sqlmodel import select
from sqlmodel.ext.asyncio.session import AsyncSession

from ..db import async_session_factory
from ..models import MarketSnapshot, Token
from .common import is_stale, log_dlq

logger = logging.getLogger("ingestion.binance")

REST_BASE = "https://data-api.binance.vision/api/v3"
SYMBOLS = ["BTCUSDT", "ETHUSDT", "SOLUSDT"]
POLL_INTERVAL_SEC = 10


async def _get_or_create_token(session: AsyncSession, symbol: str) -> Token:
    token = (await session.exec(select(Token).where(Token.address == symbol))).first()
    if token:
        return token
    token = Token(address=symbol, chain="Binance_spot", symbol=symbol.replace("USDT", ""))
    session.add(token)
    await session.commit()
    await session.refresh(token)
    return token


async def _poll_once(client: httpx.AsyncClient, session: AsyncSession, symbol: str) -> None:
    try:
        book, ticker = await asyncio.gather(
            client.get(f"{REST_BASE}/ticker/bookTicker", params={"symbol": symbol}),
            client.get(f"{REST_BASE}/ticker/24hr", params={"symbol": symbol}),
        )
        book.raise_for_status()
        ticker.raise_for_status()
        book_j, ticker_j = book.json(), ticker.json()
    except (httpx.HTTPError, ValueError) as exc:
        await log_dlq(session, "BINANCE", "PARSE_ERROR", symbol, {"error": str(exc)})
        return

    snapshot_time = datetime.fromtimestamp(ticker_j["closeTime"] / 1000, tz=timezone.utc)
    stale = is_stale(snapshot_time)
    if stale:
        await log_dlq(session, "BINANCE", "STALE_DATA", symbol, {"snapshot_time": snapshot_time.isoformat()})

    token = await _get_or_create_token(session, symbol)
    bid, ask = Decimal(book_j["bidPrice"]), Decimal(book_j["askPrice"])
    mid = (bid + ask) / 2
    spread_pct = ((ask - bid) / mid * 100) if mid else Decimal(0)

    session.add(
        MarketSnapshot(
            token_id=token.id,
            price_usd=Decimal(ticker_j["lastPrice"]),
            volume_24h_usd=Decimal(ticker_j["quoteVolume"]),
            bid_price=bid,
            ask_price=ask,
            spread_pct=spread_pct,
            source="Binance_WS",
            snapshot_time=snapshot_time,
            is_stale=stale,
        )
    )
    await session.commit()


async def run_binance_ingestion() -> None:
    async with httpx.AsyncClient(timeout=10) as client:
        while True:
            async with async_session_factory() as session:
                for symbol in SYMBOLS:
                    await _poll_once(client, session, symbol)
            await asyncio.sleep(POLL_INTERVAL_SEC)
