"""Plain-assert self-check for wallet scoring engine (FR-WLT-01, BR-01).
Run: python -m src.agents.test_wallet_scorer
"""
from datetime import datetime, timezone
from decimal import Decimal
from uuid import uuid4

from ..models import WalletObservation
from .wallet_scorer import calculate_wallet_metrics


def _mock_obs(action: str, token_id, amount_in: Decimal, amount_out: Decimal):
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
    # A loss before any profit is a drawdown against the capital that funded it (1000 -> 400).
    assert metrics["max_drawdown_pct"] == Decimal("60.00"), metrics
    assert metrics["composite_score"] < Decimal("50.00")


def test_drawdown_from_realized_equity():
    # F-29: loss, loss, win used to report 0% drawdown and earn the full +30 drawdown points (score 56.25).
    tok = uuid4()
    obs = []
    for proceeds in ("0.8", "0.8", "1.5"):
        obs += [_mock_obs("BUY", tok, Decimal("1"), Decimal("100")), _mock_obs("SELL", tok, Decimal("100"), Decimal(proceeds))]
    metrics = calculate_wallet_metrics(obs)
    # Capital 1.4 SOL (deepest point of the SOL flow); equity 1.2 -> 1.0 -> 1.5, so the drawdown is 0.4 / 1.4.
    assert metrics["max_drawdown_pct"] == Decimal("28.57"), metrics
    assert metrics["net_pnl_usd"] == Decimal("0.1000"), metrics  # SOL; the fee is already in the balance deltas
    assert metrics["composite_score"] == Decimal("39.11"), metrics


def test_sell_without_observed_buy_is_not_scored():
    # Tokens bought before the observed history have no known cost: one such sale used to score 100.
    metrics = calculate_wallet_metrics([_mock_obs("SELL", uuid4(), Decimal("100"), Decimal("5"))])
    assert metrics["total_trades"] == 0, metrics
    assert metrics["composite_score"] == Decimal("0.00"), metrics


def test_holding_duration_and_history_window():
    # FR-WLT-01: verify average holding time and 30-day activity tracking
    from datetime import timedelta
    tok = uuid4()
    t0 = datetime(2026, 1, 1, 12, 0, tzinfo=timezone.utc)
    t1 = t0 + timedelta(hours=3)  # held for 3.0 hours
    t2 = t0 + timedelta(days=35)  # history spans 35 days

    buy1 = _mock_obs("BUY", tok, Decimal("10"), Decimal("100"))
    buy1.block_time = t0
    sell1 = _mock_obs("SELL", tok, Decimal("100"), Decimal("15"))
    sell1.block_time = t1

    # Add another observation 35 days later to check 30d history detection
    tok2 = uuid4()
    buy2 = _mock_obs("BUY", tok2, Decimal("5"), Decimal("50"))
    buy2.block_time = t2

    metrics = calculate_wallet_metrics([buy1, sell1, buy2])
    assert metrics["avg_holding_time_hours"] == Decimal("3.00"), metrics
    assert metrics["history_days"] >= Decimal("35.00"), metrics
    assert metrics["has_min_history_30d"] is True, metrics


if __name__ == "__main__":
    test_empty_observations()
    test_profitable_trader_metrics()
    test_losing_trader_metrics()
    test_drawdown_from_realized_equity()
    test_sell_without_observed_buy_is_not_scored()
    test_holding_duration_and_history_window()
    print("ok")
