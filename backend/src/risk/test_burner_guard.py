"""Plain-assert self-check for Burner Wallet Guard & Safety Gate (LIVE_TRADING_SAFETY_GATE.md).
Run: python -m src.risk.test_burner_guard
"""
from decimal import Decimal
import os

from .burner_guard import (
    SafetyGateError,
    assert_paper_mode,
    pre_order_balance_guard,
    verify_two_step_approval,
)


def test_assert_paper_mode_passes_by_default():
    assert_paper_mode()


def test_assert_paper_mode_blocks_live_flag():
    os.environ["LIVE_TRADING_ENABLED"] = "TRUE"
    try:
        assert_paper_mode()
        passed = True
    except SafetyGateError:
        passed = False
    finally:
        os.environ["LIVE_TRADING_ENABLED"] = "FALSE"
    assert not passed, "SafetyGateError must be raised when LIVE_TRADING_ENABLED is TRUE"


def test_burner_wallet_balance_guard():
    # 1. Normal balance within 2 SOL limit
    assert pre_order_balance_guard("Wallet123456", Decimal("1.5"), Decimal("2.0")) is True

    # 2. Balance exceeds 2 SOL limit -> raises SafetyGateError
    try:
        pre_order_balance_guard("Wallet123456", Decimal("2.5"), Decimal("2.0"))
        blocked = False
    except SafetyGateError:
        blocked = True
    assert blocked, "Balance > limit must raise SafetyGateError"

    # 3. Limit configured above hard cap of 5 SOL -> raises SafetyGateError
    try:
        pre_order_balance_guard("Wallet123456", Decimal("1.0"), Decimal("6.0"))
        cap_enforced = False
    except SafetyGateError:
        cap_enforced = True
    assert cap_enforced, "Limit > 5.0 SOL must be rejected by hard cap"


def test_two_step_approval():
    assert verify_two_step_approval(True, "CONFIRM_RESET_123", "CONFIRM_RESET_123") is True
    assert verify_two_step_approval(False, "CONFIRM_RESET_123", "CONFIRM_RESET_123") is False
    assert verify_two_step_approval(True, "WRONG_CODE", "CONFIRM_RESET_123") is False


if __name__ == "__main__":
    test_assert_paper_mode_passes_by_default()
    test_assert_paper_mode_blocks_live_flag()
    test_burner_wallet_balance_guard()
    test_two_step_approval()
    print("ok")
