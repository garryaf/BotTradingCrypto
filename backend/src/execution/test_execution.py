"""Plain-assert self-check for [PH6] Live Trading Execution Module & Safety Gate.
Run: python -m src.execution.test_execution
"""
from decimal import Decimal
import os
from unittest.mock import patch

from ..risk.burner_guard import SafetyGateError
from .base import LiveOrderRequest
from .binance_executor import BinanceLiveExecutor
from .safety_gate import (
    LiveReadinessCertificate,
    assert_live_trading_safety_gate,
    evaluate_live_trading_prerequisites,
)
from .solana_executor import SolanaLiveExecutor

VALID_CERT = LiveReadinessCertificate(
    soak_test_30d_completed=True,
    positive_expectancy_verified=True,
    zero_crashes_verified=True,
    max_drawdown_under_8pct=True,
    kill_switch_drill_passed=True,
    burner_wallet_isolated=True,
    code_audit_completed=True,
    operator_two_step_code="CONFIRM_LIVE_OP_889",
    expected_two_step_code="CONFIRM_LIVE_OP_889",
    burner_wallet_address="Burner11111111111111111111111111111111111",
    burner_wallet_balance_sol=Decimal("1.5"),
)

BASE_REQUEST = LiveOrderRequest(
    symbol="BTCUSDT",
    side="BUY",
    quantity=Decimal("0.01"),
    target_price=Decimal("60000"),
    stop_loss=Decimal("59000"),
    venue="BINANCE_SPOT",
    confirmation_code="CONFIRM_LIVE_OP_889",
    expected_confirmation_code="CONFIRM_LIVE_OP_889",
    certificate=VALID_CERT,
)


def test_live_execution_hard_locked_by_default():
    # 1. Binance execution must be blocked by default paper mode lock
    binance = BinanceLiveExecutor()
    res_binance = binance.execute(BASE_REQUEST)
    assert res_binance.status == "REJECTED_BY_SAFETY_GATE"
    assert any("hard-locked" in r or "prohibited" in r or "SAFETY GATE" in r for r in res_binance.rejection_reasons)

    # 2. Solana execution must be blocked by default paper mode lock
    solana = SolanaLiveExecutor()
    sol_req = LiveOrderRequest(
        symbol="SOLUSDT",
        side="BUY",
        quantity=Decimal(1),
        target_price=Decimal(150),
        stop_loss=Decimal(145),
        venue="SOLANA_DEX",
        confirmation_code="CONFIRM_LIVE_OP_889",
        expected_confirmation_code="CONFIRM_LIVE_OP_889",
        certificate=VALID_CERT,
        burner_wallet_address="Burner11111111111111111111111111111111111",
        burner_wallet_balance_sol=Decimal("1.5"),
    )
    res_solana = solana.execute(sol_req)
    assert res_solana.status == "REJECTED_BY_SAFETY_GATE"
    assert any("hard-locked" in r or "prohibited" in r or "SAFETY GATE" in r for r in res_solana.rejection_reasons)


def test_safety_gate_prerequisites_validation():
    # Incomplete soak test
    bad_cert = LiveReadinessCertificate(
        soak_test_30d_completed=False,
        positive_expectancy_verified=True,
        zero_crashes_verified=True,
        max_drawdown_under_8pct=True,
        kill_switch_drill_passed=True,
        burner_wallet_isolated=True,
        code_audit_completed=True,
        operator_two_step_code="CODE",
        expected_two_step_code="CODE",
    )
    passed, reasons = evaluate_live_trading_prerequisites(bad_cert)
    assert passed is False
    assert any("Kriteria 1 FAILED" in r for r in reasons)


def test_two_step_confirmation_mismatch_blocks_order():
    bad_cert = LiveReadinessCertificate(
        soak_test_30d_completed=True,
        positive_expectancy_verified=True,
        zero_crashes_verified=True,
        max_drawdown_under_8pct=True,
        kill_switch_drill_passed=True,
        burner_wallet_isolated=True,
        code_audit_completed=True,
        operator_two_step_code="WRONG_CODE",
        expected_two_step_code="CONFIRM_LIVE_OP_889",
    )
    passed, reasons = evaluate_live_trading_prerequisites(bad_cert)
    assert passed is False
    assert any("Kriteria 6 FAILED" in r for r in reasons)


def test_solana_burner_wallet_excess_balance_blocks():
    # Balance 2.5 SOL > 2.0 SOL burner limit
    bad_cert = LiveReadinessCertificate(
        soak_test_30d_completed=True,
        positive_expectancy_verified=True,
        zero_crashes_verified=True,
        max_drawdown_under_8pct=True,
        kill_switch_drill_passed=True,
        burner_wallet_isolated=True,
        code_audit_completed=True,
        operator_two_step_code="CODE",
        expected_two_step_code="CODE",
        burner_wallet_address="Burner11111111111111111111111111111111111",
        burner_wallet_balance_sol=Decimal("2.5"),
    )
    passed, reasons = evaluate_live_trading_prerequisites(bad_cert)
    assert passed is False
    assert any("Kriteria 4 FAILED" in r for r in reasons)


def test_hypothetical_live_dispatch_when_all_prerequisites_met():
    # Simulate an approved Phase 7 state where paper_mode assertion is relaxed and all 6 criteria pass
    binance = BinanceLiveExecutor()
    with patch("src.risk.burner_guard.LIVE_TRADING_ENABLED", True), \
         patch("src.execution.base.assert_paper_mode", return_value=None), \
         patch("src.execution.safety_gate.assert_paper_mode", return_value=None):
        res = binance.execute(BASE_REQUEST)
        assert res.status == "FILLED"
        assert res.executed_price == Decimal("60000")
        assert res.order_id.startswith("BINANCE-LIVE-")


if __name__ == "__main__":
    test_live_execution_hard_locked_by_default()
    test_safety_gate_prerequisites_validation()
    test_two_step_confirmation_mismatch_blocks_order()
    test_solana_burner_wallet_excess_balance_blocks()
    test_hypothetical_live_dispatch_when_all_prerequisites_met()
    print("ok")
