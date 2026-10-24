"""Plain-assert self-check for wallet scoring engine (FR-WLT-01, BR-01).
Run: python -m src.agents.test_wallet_scorer
"""
from datetime import datetime, timezone
from decimal import Decimal
from uuid import uuid4

from ..models import WalletObservation
from .wallet_scorer import calculate_wallet_metrics


def _mock_obs(action: str, token_id, amount_in: Decimal, amount_out: Decimal, price_usd: Decimal = Decimal(0)):
    is_buy = action == "BUY"
    return WalletObservation(
        id=uuid4(),
        wallet_id=uuid4(),
        tx_signature=f"sig-{uuid4()}",
        chain="solana",
        action=action,
        token_in_id=None if is_buy else token_id,
        token_out_id=token_id if is_buy else None,
        amount_in=amount_in,
        amount_out=amount_out,
        price_usd=price_usd,
        network_fee_native=Decimal("0.000005"),
        block_time=datetime.now(timezone.utc),
    )


def test_empty_observations():
    metrics = calculate_wallet_metrics([])
    assert metrics["total_trades"] == 0
    assert metrics["win_rate_pct"] == Decimal("0.00")
    assert metrics["profit_factor"] == Decimal("0.00")
    assert metrics["composite_score"] == Decimal("0.00")


def test_profitable_trader_metrics():
    tok = uuid4()
    # Buy 100 tokens with $1000 cost basis
    buy = _mock_obs("BUY", tok, amount_in=Decimal("1000.00"), amount_out=Decimal("100.00"))
    # Sell 100 tokens for $1500 proceeds (+$500 profit)
    sell = _mock_obs("SELL", tok, amount_in=Decimal("100.00"), amount_out=Decimal("1500.00"))

    metrics = calculate_wallet_metrics([buy, sell])
    assert metrics["total_trades"] == 1
    assert metrics["win_rate_pct"] == Decimal("100.00")
    assert metrics["profit_factor"] >= Decimal("10.00")
    assert metrics["net_pnl_usd"] > Decimal("490.00")
    assert metrics["composite_score"] >= Decimal("65.00")


def test_losing_trader_metrics():
    tok = uuid4()
    # Buy 100 tokens with $1000
    buy = _mock_obs("BUY", tok, amount_in=Decimal("1000.00"), amount_out=Decimal("100.00"))
    # Sell 100 tokens for $400 (-$600 loss)
    sell = _mock_obs("SELL", tok, amount_in=Decimal("100.00"), amount_out=Decimal("400.00"))

    metrics = calculate_wallet_metrics([buy, sell])
    assert metrics["total_trades"] == 1
    assert metrics["win_rate_pct"] == Decimal("0.00")
    assert metrics["profit_factor"] == Decimal("0.00")
    assert metrics["net_pnl_usd"] < Decimal("0.00")
    assert metrics["composite_score"] < Decimal("50.00")


if __name__ == "__main__":
    test_empty_observations()
    test_profitable_trader_metrics()
    test_losing_trader_metrics()
    print("ok")
