"""Plain-assert self-check for Solana DEX AMM spread model, continuous poller, and crawler (F-16).
Run: python -m src.ingestion.test_solana_dex
"""
import asyncio
from datetime import datetime, timezone
from decimal import Decimal
from unittest.mock import AsyncMock, MagicMock
from uuid import uuid4

import httpx

from ..config import settings
from ..models import MarketSnapshot, Position, Token, Wallet
from ..risk.broker import fee_for_venue
from ..risk.engine import _execution_venue, risk_limits
from .solana import (
    DEXSCREENER_TOKENS_URL,
    RAYDIUM_AMM_PROGRAM_ID,
    _refresh_market,
    crawl_candidate_wallets,
    refresh_open_spl_positions,
)


def test_amm_spread_model_liquid_pool():
    # Liquid pool ($500,000 liquidity):
    # base fee = 0.30%, impact = 100 / 500,000 = 0.02% -> half_spread = 0.32%
    # spread = 0.64%, bid = 0.5 * (1 - 0.0032) = 0.498400, ask = 0.5 * (1 + 0.0032) = 0.501600
    token = Token(id=uuid4(), address="MintLiquid123", chain="solana", symbol="LIQ")

    def handler(request: httpx.Request) -> httpx.Response:
        assert str(request.url).startswith(f"{DEXSCREENER_TOKENS_URL}/MintLiquid123")
        return httpx.Response(
            200,
            json=[{
                "baseToken": {"address": "MintLiquid123", "symbol": "LIQ"},
                "priceUsd": "0.500000",
                "liquidity": {"usd": 500000.0},
                "volume": {"h24": 2500000.0},
            }],
        )

    mock_session = AsyncMock()
    mock_session.add = MagicMock()

    async def run():
        async with httpx.AsyncClient(transport=httpx.MockTransport(handler)) as client:
            return await _refresh_market(client, mock_session, token)

    snap = asyncio.run(run())
    assert snap is not None
    assert snap.price_usd == Decimal("0.500000")
    assert snap.pool_liquidity_usd == Decimal("500000.0")
    assert snap.volume_24h_usd == Decimal("2500000.0")
    assert snap.bid_price is not None and snap.ask_price is not None
    assert snap.bid_price < snap.price_usd < snap.ask_price
    # Check spread: ~0.64%
    assert Decimal("0.60") <= snap.spread_pct <= Decimal("0.70"), snap.spread_pct
    assert mock_session.commit.called


def test_amm_spread_model_zero_liquidity_fail_closed():
    token = Token(id=uuid4(), address="MintZero123", chain="solana", symbol="ZERO")

    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(
            200,
            json=[{
                "baseToken": {"address": "MintZero123", "symbol": "ZERO"},
                "priceUsd": "1.000000",
                "liquidity": {"usd": 0.0},
                "volume": {"h24": 0.0},
            }],
        )

    mock_session = AsyncMock()
    mock_session.add = MagicMock()

    async def run():
        async with httpx.AsyncClient(transport=httpx.MockTransport(handler)) as client:
            return await _refresh_market(client, mock_session, token)

    snap = asyncio.run(run())
    assert snap is not None
    # Zero liquidity leaves bid/ask/spread None so risk gate rejects as UNKNOWN_SPREAD_PCT (fail-closed)
    assert snap.bid_price is None
    assert snap.ask_price is None
    assert snap.spread_pct is None


def test_execution_venue_and_fees():
    assert _execution_venue("solana") == "SOLANA_DEX_SIM"
    assert _execution_venue("binance") == "Binance_SPOT_SIM"

    notional = Decimal("1000.00")
    fee_usd, gas = fee_for_venue(notional, "SOLANA_DEX_SIM", Decimal("0.0010"))
    # DEX fee is 0.30% ($3.00) + native gas
    assert fee_usd == Decimal("3.0000")
    assert gas == Decimal("0.000005")

    lim = risk_limits("SOLANA_DEX_SIM")
    assert lim["max_spread_pct"] == float(settings.max_dex_spread_pct * 100)
    assert lim["min_24h_volume_usd"] == float(settings.min_dex_24h_volume_usd)


def test_crawler_discovers_trader():
    trader = "TraderPubkey111111111111111111111111111111"

    def handler(request: httpx.Request) -> httpx.Response:
        import json
        body = json.loads(request.content)
        method = body["method"]
        if method == "getSignaturesForAddress":
            return httpx.Response(200, json={"jsonrpc": "2.0", "result": [{"signature": "sig_crawl_1"}]})
        if method == "getTransaction":
            return httpx.Response(200, json={
                "jsonrpc": "2.0",
                "result": {
                    "slot": 100,
                    "transaction": {
                        "message": {
                            "accountKeys": [
                                {"pubkey": trader, "signer": True},
                                {"pubkey": RAYDIUM_AMM_PROGRAM_ID, "signer": False},
                            ]
                        }
                    }
                }
            })
        return httpx.Response(400)

    mock_session = AsyncMock()
    mock_session.exec = AsyncMock()
    # No existing wallet found
    exec_result = MagicMock()
    exec_result.first.return_value = None
    mock_session.exec.return_value = exec_result
    mock_session.add = MagicMock()

    async def run():
        async with httpx.AsyncClient(transport=httpx.MockTransport(handler)) as client:
            return await crawl_candidate_wallets(client, mock_session, limit=1)

    discovered = asyncio.run(run())
    assert len(discovered) == 1
    assert discovered[0].address == trader
    assert discovered[0].status == "DISCOVERED"
    assert mock_session.commit.called


def test_refresh_open_spl_positions_calls_refresh_market():
    tok_id = uuid4()
    token = Token(id=tok_id, address="MintOpenPos123", chain="solana", symbol="OPOS")
    pos = Position(
        id=uuid4(),
        user_id=uuid4(),
        token_id=tok_id,
        symbol="OPOSUSDT",
        status="OPEN",
        current_quantity=Decimal("100"),
        average_entry_price=Decimal("1.00"),
        current_stop_loss=Decimal("0.95"),
        take_profit_1=Decimal("1.075"),
        take_profit_2=Decimal("1.15"),
    )

    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(
            200,
            json=[{
                "baseToken": {"address": "MintOpenPos123", "symbol": "OPOS"},
                "priceUsd": "1.050000",
                "liquidity": {"usd": 100000.0},
                "volume": {"h24": 500000.0},
            }],
        )

    mock_session = AsyncMock()
    mock_session.exec = AsyncMock()
    exec_result = MagicMock()
    exec_result.all.return_value = [pos]
    mock_session.exec.return_value = exec_result
    mock_session.get.return_value = token
    mock_session.add = MagicMock()

    async def run():
        async with httpx.AsyncClient(transport=httpx.MockTransport(handler)) as client:
            return await refresh_open_spl_positions(client, mock_session)

    snaps = asyncio.run(run())
    assert len(snaps) == 1
    assert snaps[0].price_usd == Decimal("1.050000")


if __name__ == "__main__":
    test_amm_spread_model_liquid_pool()
    test_amm_spread_model_zero_liquidity_fail_closed()
    test_execution_venue_and_fees()
    test_crawler_discovers_trader()
    test_refresh_open_spl_positions_calls_refresh_market()
    print("ok")

