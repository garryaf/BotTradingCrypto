"""[PH6] Live Trading Safety Gate Prerequisites Verification.
docs/05-security/LIVE_TRADING_SAFETY_GATE.md §2-§3 & ROADMAP.md Fase 7.

Validates all 6 mandatory prerequisites before live capital execution can be unlocked:
1. 30-Day continuous paper trading observation completed.
2. Zero unhandled crashes and Max Drawdown < 8.0%.
3. Emergency stop kill-switch drill passed (<= 2.0s latency across 5 runs).
4. Burner wallet isolation enforced (balance <= 2.0 SOL, hard cap 5.0 SOL).
5. Independent code audit verified.
6. 2-Step explicit operator confirmation code.
"""
from dataclasses import dataclass, field
from decimal import Decimal
import logging

from ..risk.burner_guard import (
    DEFAULT_BURNER_WALLET_SOL_LIMIT,
    HARD_MAX_BURNER_WALLET_LIMIT,
    SafetyGateError,
    assert_paper_mode,
    pre_order_balance_guard,
    verify_two_step_approval,
)

logger = logging.getLogger("execution.safety_gate")


@dataclass
class LiveReadinessCertificate:
    """Audit certificate required before any live trading order can be submitted."""
    soak_test_30d_completed: bool = False
    positive_expectancy_verified: bool = False
    zero_crashes_verified: bool = False
    max_drawdown_under_8pct: bool = False
    kill_switch_drill_passed: bool = False
    burner_wallet_isolated: bool = False
    code_audit_completed: bool = False
    operator_two_step_code: str = ""
    expected_two_step_code: str = ""
    burner_wallet_address: str = ""
    burner_wallet_balance_sol: Decimal = Decimal(0)
    audit_notes: list[str] = field(default_factory=list)


def evaluate_live_trading_prerequisites(cert: LiveReadinessCertificate) -> tuple[bool, list[str]]:
    """Checks all 6 criteria of LIVE_TRADING_SAFETY_GATE.md. Returns (passed, failure_reasons)."""
    failures: list[str] = []

    # Layer 2 & compile-time paper mode assertion
    try:
        assert_paper_mode()
    except SafetyGateError as exc:
        failures.append(str(exc))

    # Kriteria 1: 30-Day soak test
    if not cert.soak_test_30d_completed:
        failures.append("Kriteria 1 FAILED: 30-Day continuous paper soak test not completed.")
    if not cert.positive_expectancy_verified:
        failures.append("Kriteria 1 FAILED: Positive portfolio expectancy (E > 0) not verified.")

    # Kriteria 2: Zero crash & Drawdown < 8%
    if not cert.zero_crashes_verified:
        failures.append("Kriteria 2 FAILED: Zero unhandled background crash requirement not satisfied.")
    if not cert.max_drawdown_under_8pct:
        failures.append("Kriteria 2 FAILED: Historical maximum drawdown exceeded 8.0% limit.")

    # Kriteria 3: Kill switch drill <= 2.0s
    if not cert.kill_switch_drill_passed:
        failures.append("Kriteria 3 FAILED: Emergency stop kill switch drill (<= 2.0s) not verified.")

    # Kriteria 4: Burner wallet isolation
    if not cert.burner_wallet_isolated:
        failures.append("Kriteria 4 FAILED: Burner wallet capital isolation not verified.")
    if cert.burner_wallet_address:
        try:
            pre_order_balance_guard(cert.burner_wallet_address, cert.burner_wallet_balance_sol)
        except SafetyGateError as exc:
            failures.append(f"Kriteria 4 FAILED: {exc}")

    # Kriteria 5: Code audit
    if not cert.code_audit_completed:
        failures.append("Kriteria 5 FAILED: Independent transaction code audit not completed.")

    # Kriteria 6: 2-step operator confirmation
    if not verify_two_step_approval(True, cert.operator_two_step_code, cert.expected_two_step_code):
        failures.append("Kriteria 6 FAILED: Explicit 2-step operator confirmation code mismatch or missing.")

    passed = len(failures) == 0
    return passed, failures


def assert_live_trading_safety_gate(cert: LiveReadinessCertificate) -> None:
    """Raises SafetyGateError if any prerequisite is unfulfilled."""
    passed, failures = evaluate_live_trading_prerequisites(cert)
    if not passed:
        msg = "[LIVE TRADING SAFETY GATE] Execution BLOCKED. Prerequisite checklist failures:\n - " + "\n - ".join(failures)
        logger.error(msg)
        raise SafetyGateError(msg)

