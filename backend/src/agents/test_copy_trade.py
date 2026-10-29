"""Plain-assert self-check for copy-trading signal generation (BR-01, COPY_TRADING_FLOWCHART.mmd).
Run: python -m src.agents.test_copy_trade
"""
import asyncio
from decimal import Decimal
from unittest.mock import AsyncMock, MagicMock
from uuid import uuid4

from .copy_trade import create_copy_trade_signal, validate_copy_trade_preconditions
from ..models import Token, TradingSignal, Wallet


def _mock_wallet(status: str = "APPROVED", score: Decimal = Decimal("85.00")) -> Wallet:
    return Wallet(
        id=uuid4(),
        address=f"Wall{uuid4()}",
        chain="solana",
        status=status,
        composite_score=score,
        win_rate_pct=Decimal("75.00"),
    )


def _mock_token(
    freeze_revoked: bool = True,
    mint_revoked: bool = True,
    liquidity: Decimal = Decimal("50000.00"),
) -> Token:
    return Token(
        id=uuid4(),
        address=f"Mint{uuid4()}",
        chain="solana",
        symbol="MEME",
        freeze_authority_revoked=freeze_revoked,
        mint_authority_revoked=mint_revoked,
        pool_liquidity_usd=liquidity,
    )


def test_validate_preconditions_unmonitored_wallet():
    wallet = _mock_wallet(status="DISCOVERED")
    token = _mock_token()
    valid, reason = validate_copy_trade_preconditions(wallet, token, "BUY", Decimal("100.00"))
    assert not valid
    assert reason == "WALLET_NOT_MONITORED"


def test_validate_preconditions_unsafe_token():
    wallet = _mock_wallet(status="APPROVED")
    token = _mock_token(freeze_revoked=False)
    valid, reason = validate_copy_trade_preconditions(wallet, token, "BUY", Decimal("100.00"))
    assert not valid
    assert reason == "TOKEN_UNSAFE_AUTHORITY_NOT_REVOKED"


def test_validate_preconditions_low_liquidity():
    wallet = _mock_wallet(status="APPROVED")
    token = _mock_token(liquidity=Decimal("5000.00"))  # < $20,000 threshold
    valid, reason = validate_copy_trade_preconditions(wallet, token, "BUY", Decimal("100.00"))
    assert not valid
    assert reason == "INSUFFICIENT_POOL_LIQUIDITY"


def test_validate_preconditions_sell_not_mirrored():
    # A master SELL is an exit; mirroring it as a new entry opened a long (F-27).
    valid, reason = validate_copy_trade_preconditions(_mock_wallet(), _mock_token(), "SELL", Decimal("100.00"))
    assert not valid
    assert reason == "SELL_NOT_MIRRORED"


def test_validate_preconditions_success():
    wallet = _mock_wallet(status="ACTIVE_MONITORED")
    token = _mock_token()
    valid, reason = validate_copy_trade_preconditions(wallet, token, "BUY", Decimal("150.00"))
    assert valid
    assert reason is None


def test_create_copy_trade_signal_success():
    wallet = _mock_wallet(status="APPROVED", score=Decimal("80.00"))
    token = _mock_token()
    price = Decimal("100.00")

    mock_session = AsyncMock()
    mock_session.add = MagicMock()

    async def run():
        return await create_copy_trade_signal(mock_session, wallet, token, "BUY", price)

    signal = asyncio.run(run())
    assert signal is not None
    assert signal.action == "BUY"
    assert signal.target_entry_price == Decimal("100.00")
    assert signal.suggested_stop_loss == Decimal("95.00")
    assert signal.suggested_take_profit_1 == Decimal("107.50")
    assert signal.suggested_take_profit_2 == Decimal("115.00")
    assert signal.status == "PENDING"
    assert signal.confidence_score == Decimal("0.800")
    assert signal.estimated_winrate_pct == Decimal("75.00")
    assert mock_session.commit.called


if __name__ == "__main__":
    test_validate_preconditions_unmonitored_wallet()
    test_validate_preconditions_unsafe_token()
    test_validate_preconditions_low_liquidity()
    test_validate_preconditions_sell_not_mirrored()
    test_validate_preconditions_success()
    test_create_copy_trade_signal_success()
    print("ok")
