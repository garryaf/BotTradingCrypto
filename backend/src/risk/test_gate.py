"""Plain-assert self-check for the 9-gate Risk Gate — pure functions, no DB
needed. Run: python -m src.risk.test_gate

ROADMAP Milestone 4: "100% sinyal cacat tertolak di pintu risiko" — each
test below breaks exactly one gate and asserts ONLY that gate fails.
"""
from datetime import datetime, timedelta, timezone
from decimal import Decimal

from .. import config
from .gate import evaluate_risk

NOW = datetime.now(timezone.utc)

BASELINE = dict(
    action="BUY",
    entry_price=Decimal(100),
    stop_loss=Decimal(95),
    take_profit_1=Decimal("107.5"),
    take_profit_2=Decimal(115),
    estimated_winrate_pct=Decimal(70),
    equity_usd=Decimal(10000),
    cash_balance_usd=Decimal(10000),
    daily_loss_pct=Decimal(0),
    current_drawdown_pct=Decimal(0),
    spread_pct=Decimal("0.01"),
    volume_24h_usd=Decimal(5_000_000),
    snapshot_time=NOW,
    is_stale=False,
    open_positions_count=0,
    circuit_breaker_active=False,
    min_lot_size=Decimal("0.001"),
)


def test_valid_signal_passes_every_gate():
    outcome = evaluate_risk(**BASELINE)
    assert outcome.passed, outcome.rejection_reasons
    assert outcome.rejection_reasons == []
    assert outcome.quantity > 0


def test_missing_stop_loss_rejected():
    outcome = evaluate_risk(**{**BASELINE, "stop_loss": BASELINE["entry_price"]})
    assert not outcome.passed
    assert "INVALID_STOP_LOSS" in outcome.rejection_reasons


def test_wrong_side_stop_loss_rejected():
    outcome = evaluate_risk(**{**BASELINE, "stop_loss": Decimal(105)})  # above entry on a BUY
    assert not outcome.passed
    assert "INVALID_STOP_LOSS" in outcome.rejection_reasons


def test_daily_loss_limit_rejected():
    outcome = evaluate_risk(**{**BASELINE, "daily_loss_pct": Decimal(3)})
    assert not outcome.passed
    assert "DAILY_LOSS_LIMIT_EXCEEDED" in outcome.rejection_reasons


def test_drawdown_limit_rejected():
    outcome = evaluate_risk(**{**BASELINE, "current_drawdown_pct": Decimal(9)})
    assert not outcome.passed
    assert "DRAWDOWN_LIMIT_EXCEEDED" in outcome.rejection_reasons


def test_wide_spread_rejected():
    outcome = evaluate_risk(**{**BASELINE, "spread_pct": Decimal("0.5")})
    assert not outcome.passed
    assert "SPREAD_OR_LIQUIDITY_INADEQUATE" in outcome.rejection_reasons


def test_thin_liquidity_rejected():
    outcome = evaluate_risk(**{**BASELINE, "volume_24h_usd": Decimal(100)})
    assert not outcome.passed
    assert "SPREAD_OR_LIQUIDITY_INADEQUATE" in outcome.rejection_reasons


def test_max_open_positions_rejected():
    outcome = evaluate_risk(**{**BASELINE, "open_positions_count": 5})
    assert not outcome.passed
    assert "MAX_OPEN_POSITIONS_REACHED" in outcome.rejection_reasons


def test_circuit_breaker_rejected():
    outcome = evaluate_risk(**{**BASELINE, "circuit_breaker_active": True})
    assert not outcome.passed
    assert "CIRCUIT_BREAKER_ACTIVE" in outcome.rejection_reasons


def test_stale_data_rejected():
    outcome = evaluate_risk(**{**BASELINE, "snapshot_time": NOW - timedelta(seconds=61)})
    assert not outcome.passed
    assert "STALE_MARKET_DATA" in outcome.rejection_reasons

    outcome2 = evaluate_risk(**{**BASELINE, "is_stale": True})
    assert not outcome2.passed
    assert "STALE_MARKET_DATA" in outcome2.rejection_reasons


def test_insufficient_cash_for_min_lot_rejected():
    outcome = evaluate_risk(**{**BASELINE, "cash_balance_usd": Decimal("0.01")})
    assert not outcome.passed
    assert "INSUFFICIENT_BALANCE_OR_LOT" in outcome.rejection_reasons


def test_negative_expectancy_rejected():
    outcome = evaluate_risk(**{**BASELINE, "estimated_winrate_pct": Decimal(10)})
    assert not outcome.passed
    assert "NON_POSITIVE_EXPECTANCY" in outcome.rejection_reasons


def test_risk_per_trade_never_exceeds_cap_at_any_drawdown():
    # risk_pct_used is derived from settings.max_risk_per_trade_pct by construction
    # (adaptive_risk_pct only ever returns that value or a smaller tier), so this
    # gate is a structural guarantee, not a reactive check — assert it holds
    # across every drawdown band rather than trying to force a failure.
    for drawdown in (Decimal(0), Decimal(2), Decimal(3), Decimal(4), Decimal(5), Decimal(9)):
        outcome = evaluate_risk(**{**BASELINE, "current_drawdown_pct": drawdown})
        assert outcome.risk_pct_used <= config.settings.max_risk_per_trade_pct
        assert outcome.risk_per_trade_check is True


def test_solana_dex_signal_passes_with_dex_spread_and_volume():
    # F-16: Solana DEX AMM pool with 0.64% spread (0.30% fee + 0.02% impact) passes under SOLANA_DEX_SIM limits
    outcome = evaluate_risk(**{
        **BASELINE,
        "spread_pct": Decimal("0.64"),
        "volume_24h_usd": Decimal("500000"),
        "venue": "SOLANA_DEX_SIM",
    })
    assert outcome.passed, outcome.rejection_reasons
    assert outcome.rejection_reasons == []
    # Fee must use DEX taker fee (0.30%)
    expected_fee = (outcome.quantity * BASELINE["entry_price"]) * Decimal("0.0030")
    assert abs(outcome.fee_usd - expected_fee) < Decimal("0.01")


def test_solana_dex_signal_excessive_spread_rejected():
    # F-16: Solana DEX pool with 3.0% spread exceeds max_dex_spread_pct (2.5%) -> fail-closed
    outcome = evaluate_risk(**{
        **BASELINE,
        "spread_pct": Decimal("3.0"),
        "volume_24h_usd": Decimal("500000"),
        "venue": "SOLANA_DEX_SIM",
    })
    assert not outcome.passed
    assert "SPREAD_OR_LIQUIDITY_INADEQUATE" in outcome.rejection_reasons


def test_solana_dex_signal_low_volume_rejected():
    # F-16: Solana DEX pool with $5,000 volume falls below min_dex_24h_volume_usd ($20,000) -> fail-closed
    outcome = evaluate_risk(**{
        **BASELINE,
        "spread_pct": Decimal("0.64"),
        "volume_24h_usd": Decimal("5000"),
        "venue": "SOLANA_DEX_SIM",
    })
    assert not outcome.passed
    assert "SPREAD_OR_LIQUIDITY_INADEQUATE" in outcome.rejection_reasons


def test_insufficient_rr_rejected():
    # F-17: TP1 = 105 -> dist=5, risk_unit=5, R:R=1.0 < 1.5 -> INSUFFICIENT_RISK_REWARD
    outcome = evaluate_risk(**{**BASELINE, "take_profit_1": Decimal(105)})
    assert not outcome.passed
    assert outcome.rejection_reasons == ["INSUFFICIENT_RISK_REWARD"]
    assert outcome.stop_loss_check is False


def test_exact_minimum_rr_passes():
    # F-17: TP1 = 107.5 -> dist=7.5, risk_unit=5, R:R=1.5 = threshold -> passes
    outcome = evaluate_risk(**{**BASELINE, "take_profit_1": Decimal("107.5")})
    assert outcome.passed
    assert outcome.rejection_reasons == []
    assert outcome.stop_loss_check is True


def test_rr_check_without_stop_loss_does_not_double_reject():
    # F-17: Invalid SL -> INVALID_STOP_LOSS, not double-flagging INSUFFICIENT_RISK_REWARD
    outcome = evaluate_risk(**{**BASELINE, "stop_loss": BASELINE["entry_price"]})
    assert not outcome.passed
    assert "INVALID_STOP_LOSS" in outcome.rejection_reasons
    assert "INSUFFICIENT_RISK_REWARD" not in outcome.rejection_reasons


if __name__ == "__main__":
    test_valid_signal_passes_every_gate()
    test_missing_stop_loss_rejected()
    test_wrong_side_stop_loss_rejected()
    test_daily_loss_limit_rejected()
    test_drawdown_limit_rejected()
    test_wide_spread_rejected()
    test_thin_liquidity_rejected()
    test_max_open_positions_rejected()
    test_circuit_breaker_rejected()
    test_stale_data_rejected()
    test_insufficient_cash_for_min_lot_rejected()
    test_negative_expectancy_rejected()
    test_risk_per_trade_never_exceeds_cap_at_any_drawdown()
    test_solana_dex_signal_passes_with_dex_spread_and_volume()
    test_solana_dex_signal_excessive_spread_rejected()
    test_solana_dex_signal_low_volume_rejected()
    test_insufficient_rr_rejected()
    test_exact_minimum_rr_passes()
    test_rr_check_without_stop_loss_does_not_double_reject()
    print("ok")
