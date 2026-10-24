"""Integration / Unit test for Binance Spot market ingestion (FR-MKT-01, AC-ING-03).
Run: python -m src.ingestion.test_binance
"""
import asyncio
from datetime import datetime, timezone
from decimal import Decimal
from unittest.mock import AsyncMock, MagicMock
from uuid import uuid4

import httpx

from .binance import _poll_once
from ..models import MarketSnapshot, Token


def test_binance_poll_once_success():
    now_ms = int(datetime.now(timezone.utc).timestamp() * 1000)

    def handler(request: httpx.Request) -> httpx.Response:
        url = str(request.url)
        if "bookTicker" in url:
            return httpx.Response(200, json={"bidPrice": "65000.00", "askPrice": "65005.00"})
        if "24hr" in url:
            return httpx.Response(
                200,
                json={
                    "lastPrice": "65002.50",
                    "quoteVolume": "125000000.00",
                    "closeTime": now_ms,
                },
            )
        return httpx.Response(404)

    mock_token = Token(id=uuid4(), address="BTCUSDT", chain="Binance_spot", symbol="BTC")
    mock_session = AsyncMock()
    mock_session.add = MagicMock()

    # Mock the _get_or_create_token query
    mock_result = MagicMock()
    mock_result.first.return_value = mock_token
    mock_session.exec.return_value = mock_result

    async def run():
        async with httpx.AsyncClient(transport=httpx.MockTransport(handler)) as client:
            await _poll_once(client, mock_session, "BTCUSDT")

    asyncio.run(run())

    assert mock_session.add.called
    added = mock_session.add.call_args[0][0]
    assert isinstance(added, MarketSnapshot)
    assert added.price_usd == Decimal("65002.50")
    assert added.volume_24h_usd == Decimal("125000000.00")
    assert added.bid_price == Decimal("65000.00")
    assert added.ask_price == Decimal("65005.00")
    assert added.is_stale is False
    assert mock_session.commit.called


def test_binance_poll_once_stale_data():
    # closeTime 60 seconds ago (exceeds 30s threshold -> stale)
    old_ms = int((datetime.now(timezone.utc).timestamp() - 60) * 1000)

    def handler(request: httpx.Request) -> httpx.Response:
        url = str(request.url)
        if "bookTicker" in url:
            return httpx.Response(200, json={"bidPrice": "150.00", "askPrice": "150.10"})
        if "24hr" in url:
            return httpx.Response(
                200,
                json={"lastPrice": "150.05", "quoteVolume": "5000000.00", "closeTime": old_ms},
            )
        return httpx.Response(404)

    mock_token = Token(id=uuid4(), address="SOLUSDT", chain="Binance_spot", symbol="SOL")
    mock_session = AsyncMock()
    mock_session.add = MagicMock()
    mock_result = MagicMock()
    mock_result.first.return_value = mock_token
    mock_session.exec.return_value = mock_result

    async def run():
        async with httpx.AsyncClient(transport=httpx.MockTransport(handler)) as client:
            await _poll_once(client, mock_session, "SOLUSDT")

    asyncio.run(run())

    # Snapshot added with is_stale = True
    added_snapshot = [call[0][0] for call in mock_session.add.call_args_list if isinstance(call[0][0], MarketSnapshot)]
    assert len(added_snapshot) == 1
    assert added_snapshot[0].is_stale is True


def test_binance_poll_once_network_error_logs_dlq():
    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(500, json={"error": "Binance server error"})

    mock_session = AsyncMock()
    mock_session.add = MagicMock()

    async def run():
        async with httpx.AsyncClient(transport=httpx.MockTransport(handler)) as client:
            await _poll_once(client, mock_session, "ETHUSDT")

    asyncio.run(run())

    # Ensure DLQ record was added
    from ..models import IngestionError
    dlq_calls = [call[0][0] for call in mock_session.add.call_args_list if isinstance(call[0][0], IngestionError)]
    assert len(dlq_calls) == 1
    assert dlq_calls[0].source == "BINANCE"
    assert dlq_calls[0].reason == "PARSE_ERROR"


if __name__ == "__main__":
    test_binance_poll_once_success()
    test_binance_poll_once_stale_data()
    test_binance_poll_once_network_error_logs_dlq()
    print("ok")
