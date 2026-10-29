"""Tests for anti-manipulation screening — FR-WLT-02.
Run: python -m src.agents.test_anti_manipulation
"""
from datetime import datetime, timedelta, timezone
from decimal import Decimal
from uuid import uuid4

from ..models import WalletObservation
from .anti_manipulation import (
    WASH_WINDOW_SECONDS,
    ManipulationFlags,
    screen_wallet,
)


# ─── Helpers ──────────────────────────────────────────────────────────────────

def _obs(
    action: str,
    token_id,
    amount_in: Decimal,
    amount_out: Decimal,
    block_time: datetime,
) -> WalletObservation:
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
        block_time=block_time,
    )


T0 = datetime(2026, 1, 1, 12, 0, 0, tzinfo=timezone.utc)


def _t(offset_seconds: int) -> datetime:
    return T0 + timedelta(seconds=offset_seconds)


def _metrics(total_trades: int = 1, gross_profit: float = 1.0) -> dict:
    return {
        "total_trades": total_trades,
        "win_rate_pct": Decimal("100.00"),
        "profit_factor": Decimal("10.00"),
        "net_pnl_usd": Decimal(str(gross_profit)),
        "max_drawdown_pct": Decimal("0.00"),
        "composite_score": Decimal("85.00"),
    }


# ─── Tests ────────────────────────────────────────────────────────────────────

def test_clean_wallet_passes():
    """A normal profitable wallet with well-spaced trades on DIFFERENT tokens is not flagged."""
    tok_a = uuid4()
    tok_b = uuid4()
    obs = [
        _obs("BUY",  tok_a, Decimal("1.0"), Decimal("100"), _t(0)),
        _obs("SELL", tok_a, Decimal("100"), Decimal("1.5"), _t(3600)),   # 1 hour later, tok_a
        _obs("BUY",  tok_b, Decimal("1.0"), Decimal("100"), _t(7200)),
        _obs("SELL", tok_b, Decimal("100"), Decimal("1.4"), _t(10800)),  # another hour, tok_b
    ]
    result = screen_wallet(obs, _metrics(total_trades=2))
    assert result.is_clean, f"Expected clean, got: {result.reasons}"
    assert not result.wash_trade_detected
    assert not result.one_hit_wonder_detected


def test_empty_observations_passes():
    result = screen_wallet([], _metrics(total_trades=0))
    assert result.is_clean


def test_wash_trade_rapid_near_zero_pnl():
    """BUY→SELL within 5 min with ~0% PnL should be flagged as wash trade."""
    tok = uuid4()
    obs = []
    # Two suspicious round-trips (threshold = 2)
    for i in range(2):
        base = i * 10000
        obs += [
            _obs("BUY",  tok, Decimal("1.000"), Decimal("100"), _t(base + 0)),
            _obs("SELL", tok, Decimal("100"),   Decimal("1.002"), _t(base + 60)),  # 1 min, +0.2% PnL ≤ 1%
        ]

    result = screen_wallet(obs, _metrics(total_trades=2))
    assert result.wash_trade_detected, "Expected wash trade flag"
    assert result.wash_suspicious_pairs >= 2
    assert not result.is_clean
    assert any("WASH_TRADE" in r for r in result.reasons)


def test_wash_trade_rapid_but_real_profit_is_clean():
    """BUY→SELL within 5 min but with +5% PnL — legitimate scalp, not wash."""
    tok = uuid4()
    obs = [
        _obs("BUY",  tok, Decimal("1.000"), Decimal("100"), _t(0)),
        _obs("SELL", tok, Decimal("100"),   Decimal("1.060"), _t(120)),  # +6% in 2 min
        _obs("BUY",  tok, Decimal("1.000"), Decimal("100"), _t(5000)),
        _obs("SELL", tok, Decimal("100"),   Decimal("1.055"), _t(5120)),  # +5.5%
    ]
    result = screen_wallet(obs, _metrics(total_trades=2))
    # Should NOT be flagged as wash trade (net PnL > 1% threshold)
    assert not result.wash_trade_detected, f"False positive wash trade: {result.reasons}"


def test_wash_trade_only_one_pair_not_flagged():
    """Single suspicious pair is under the threshold (need >= 2)."""
    tok = uuid4()
    obs = [
        _obs("BUY",  tok, Decimal("1.000"), Decimal("100"), _t(0)),
        _obs("SELL", tok, Decimal("100"),   Decimal("0.999"), _t(60)),   # ~0% PnL, 1 min
    ]
    result = screen_wallet(obs, _metrics(total_trades=1))
    assert not result.wash_trade_detected, "Single suspicious pair should not trigger wash flag"


def test_wash_trade_after_window_is_clean():
    """BUY→SELL after WASH_WINDOW_SECONDS should not be flagged."""
    tok = uuid4()
    outside_window = WASH_WINDOW_SECONDS + 60
    obs = []
    for i in range(3):
        base = i * (outside_window + 100)
        obs += [
            _obs("BUY",  tok, Decimal("1.0"), Decimal("100"), _t(base)),
            _obs("SELL", tok, Decimal("100"), Decimal("1.001"), _t(base + outside_window)),
        ]
    result = screen_wallet(obs, _metrics(total_trades=3))
    assert not result.wash_trade_detected, f"Outside-window trades flagged: {result.reasons}"


def test_one_hit_wonder_single_token_small_history():
    """Single winning token with only 1 trade = 1-hit wonder."""
    tok_a = uuid4()
    obs = [
        _obs("BUY",  tok_a, Decimal("1.0"), Decimal("100"), _t(0)),
        _obs("SELL", tok_a, Decimal("100"), Decimal("10.0"), _t(3600)),  # 10x
    ]
    result = screen_wallet(obs, _metrics(total_trades=1))
    assert result.one_hit_wonder_detected, f"Expected 1-hit wonder, got: {result.reasons}"
    assert not result.is_clean
    assert any("ONE_HIT_WONDER" in r for r in result.reasons)


def test_one_hit_wonder_diverse_tokens_is_clean():
    """Profits spread across multiple tokens — not a 1-hit wonder."""
    obs = []
    for _ in range(4):
        tok = uuid4()
        obs += [
            _obs("BUY",  tok, Decimal("1.0"),  Decimal("100"), _t(len(obs) * 1000)),
            _obs("SELL", tok, Decimal("100"),  Decimal("1.3"),  _t(len(obs) * 1000 + 500)),
        ]
    result = screen_wallet(obs, _metrics(total_trades=4))
    assert not result.one_hit_wonder_detected, f"False positive 1-hit: {result.reasons}"


def test_one_hit_wonder_high_trade_count_not_flagged():
    """Even with 1 dominant token, skip 1-hit check if total_trades > threshold (5)."""
    tok = uuid4()
    obs = []
    for i in range(6):
        obs += [
            _obs("BUY",  tok, Decimal("1.0"), Decimal("100"), _t(i * 10000)),
            _obs("SELL", tok, Decimal("100"), Decimal("1.5"),  _t(i * 10000 + 3600)),
        ]
    # Explicitly pass total_trades=6 so the check is skipped
    result = screen_wallet(obs, _metrics(total_trades=6))
    # High trade count → specialisation, not 1-hit wonder
    assert not result.one_hit_wonder_detected, f"High trade count should skip 1-hit check: {result.reasons}"


def test_both_flags_raised_simultaneously():
    """A wallet that is both wash-trading and 1-hit-wonder is doubly flagged."""
    tok = uuid4()
    obs = [
        _obs("BUY",  tok, Decimal("1.000"), Decimal("100"), _t(0)),
        _obs("SELL", tok, Decimal("100"),   Decimal("1.001"), _t(60)),
        _obs("BUY",  tok, Decimal("1.000"), Decimal("100"), _t(1000)),
        _obs("SELL", tok, Decimal("100"),   Decimal("1.002"), _t(1060)),
    ]
    result = screen_wallet(obs, _metrics(total_trades=2))
    assert not result.is_clean
    assert result.wash_trade_detected
    assert result.one_hit_wonder_detected
    assert len(result.reasons) == 2


if __name__ == "__main__":
    test_clean_wallet_passes()
    test_empty_observations_passes()
    test_wash_trade_rapid_near_zero_pnl()
    test_wash_trade_rapid_but_real_profit_is_clean()
    test_wash_trade_only_one_pair_not_flagged()
    test_wash_trade_after_window_is_clean()
    test_one_hit_wonder_single_token_small_history()
    test_one_hit_wonder_diverse_tokens_is_clean()
    test_one_hit_wonder_high_trade_count_not_flagged()
    test_both_flags_raised_simultaneously()
    print("ok")
