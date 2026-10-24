"""Live Trading Safety Gate & Burner Wallet Guard — LIVE_TRADING_SAFETY_GATE.md §1-§2.

Enforces 3-layer architecture lock:
1. Compile-time constant LIVE_TRADING_ENABLED = False.
2. Runtime assertion assert_paper_mode().
3. Pre-order balance guard (hard cap 2.0 SOL, maximum allowable 5.0 SOL) and 2-step confirmation.
"""
from decimal import Decimal
import logging
import os

logger = logging.getLogger("risk.burner_guard")

# Layer 1: Compile-time constant — locked to False in MVP (ADR-004)
LIVE_TRADING_ENABLED: bool = False
DEFAULT_BURNER_WALLET_SOL_LIMIT = Decimal("2.0")
HARD_MAX_BURNER_WALLET_LIMIT = Decimal("5.0")


class SafetyGateError(RuntimeError):
    """Raised when a live trading safety gate condition is violated."""
    pass


def assert_paper_mode() -> None:
    """Hard block: verifies that live trading is completely disabled both in env and compile-time."""
    env_val = os.getenv("LIVE_TRADING_ENABLED", "FALSE").upper()
    if env_val not in ("FALSE", "0", ""):
        raise SafetyGateError("[SAFETY GATE] Live trading flag detected in environment — execution BLOCKED. Paper mode required.")

    if LIVE_TRADING_ENABLED is not False:
        raise SafetyGateError("[SAFETY GATE] Compile-time constant override detected — execution BLOCKED.")


def pre_order_balance_guard(
    wallet_address: str,
    balance_sol: Decimal,
    limit_sol: Decimal = DEFAULT_BURNER_WALLET_SOL_LIMIT,
) -> bool:
    """Enforces burner wallet capital isolation: rejects orders if balance exceeds limit (AC-OPS-04)."""
    if limit_sol > HARD_MAX_BURNER_WALLET_LIMIT:
        raise SafetyGateError(
            f"[BURNER WALLET GUARD] Configured limit {limit_sol} SOL exceeds absolute hard cap {HARD_MAX_BURNER_WALLET_LIMIT} SOL."
        )

    if balance_sol > limit_sol:
        raise SafetyGateError(
            f"[BURNER WALLET GUARD] Wallet {wallet_address[:8]}... balance {balance_sol:.4f} SOL exceeds "
            f"allowed burner limit {limit_sol:.4f} SOL. Order BLOCKED. Transfer excess funds before proceeding."
        )

    logger.info("[BURNER WALLET GUARD] Wallet %s balance %.4f SOL <= %.4f SOL — PASSED", wallet_address[:8], balance_sol, limit_sol)
    return True


def verify_two_step_approval(user_confirmed: bool, confirmation_code: str, expected_code: str) -> bool:
    """Requires 2-step human-in-the-loop confirmation before sensitive operational changes."""
    if not user_confirmed:
        return False
    if not confirmation_code or confirmation_code.strip() != expected_code.strip():
        return False
    return True
