"""[PH6] Live Order Execution Base Architecture & Enforcers.
docs/05-security/LIVE_TRADING_SAFETY_GATE.md §1-§2 & ROADMAP.md Fase 7.

Architecture Guardrails:
1. Every executor extends BaseLiveExecutor.
2. Every call to execute() must pass _enforce_safety_gate() before ANY live order can be built or sent.
3. Fail-Closed: If LIVE_TRADING_ENABLED is False (Phase 0-6 baseline), execution is unconditionally rejected.
4. Capital Isolation: Solana execution requires a validated Burner Wallet with balance <= 2.0 SOL.
"""
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from decimal import Decimal
import logging
from typing import Any

from ..risk.burner_guard import (
    DEFAULT_BURNER_WALLET_SOL_LIMIT,
    SafetyGateError,
    assert_paper_mode,
    pre_order_balance_guard,
    verify_two_step_approval,
)
from .safety_gate import LiveReadinessCertificate, assert_live_trading_safety_gate

logger = logging.getLogger("execution.base")


@dataclass
class LiveOrderRequest:
    symbol: str
    side: str  # "BUY" or "SELL"
    quantity: Decimal
    target_price: Decimal
    stop_loss: Decimal
    venue: str  # "BINANCE_SPOT" or "SOLANA_DEX"
    confirmation_code: str
    expected_confirmation_code: str
    certificate: LiveReadinessCertificate
    burner_wallet_address: str | None = None
    burner_wallet_balance_sol: Decimal | None = None
    extra_metadata: dict[str, Any] = field(default_factory=dict)


@dataclass
class LiveOrderResult:
    order_id: str
    status: str  # "FILLED" | "REJECTED_BY_SAFETY_GATE" | "FAILED"
    venue: str
    executed_price: Decimal = Decimal(0)
    executed_quantity: Decimal = Decimal(0)
    fee_usd: Decimal = Decimal(0)
    transaction_hash: str | None = None
    rejection_reasons: list[str] = field(default_factory=list)


class BaseLiveExecutor(ABC):
    """Abstract base class for Live Order Executors.

    Enforces all 3 layers of safety before dispatching any live order to external exchanges.
    """

    def __init__(self, venue_name: str):
        self.venue_name = venue_name

    def _enforce_safety_gate(self, request: LiveOrderRequest) -> None:
        """Enforces all safety gate conditions. Raises SafetyGateError on any violation."""
        # Layer 1 & 2: Hard paper mode lock
        assert_paper_mode()

        from ..risk.burner_guard import LIVE_TRADING_ENABLED
        if not LIVE_TRADING_ENABLED:
            raise SafetyGateError(
                "[SAFETY GATE] LIVE_TRADING_ENABLED is hard-locked to False (Phase 0-6). "
                "Real capital execution is prohibited by safety policy."
            )

        # Validate prerequisite certificate
        assert_live_trading_safety_gate(request.certificate)

        # 2-step operator code verification
        if not verify_two_step_approval(True, request.confirmation_code, request.expected_confirmation_code):
            raise SafetyGateError("[SAFETY GATE] 2-step human operator confirmation failed.")

        # Venue-specific checks (e.g. Burner Wallet for Solana DEX)
        if self.venue_name == "SOLANA_DEX":
            if not request.burner_wallet_address or request.burner_wallet_balance_sol is None:
                raise SafetyGateError("[BURNER WALLET GUARD] Solana live order requires verified burner wallet.")
            pre_order_balance_guard(request.burner_wallet_address, request.burner_wallet_balance_sol)

    def execute(self, request: LiveOrderRequest) -> LiveOrderResult:
        """Entrypoint for live execution. Fail-closed on any safety check violation."""
        try:
            self._enforce_safety_gate(request)
        except SafetyGateError as exc:
            logger.warning("[SAFETY GATE BLOCKED] Live order for %s rejected: %s", request.symbol, exc)
            return LiveOrderResult(
                order_id=f"LIVE-BLOCKED-{request.symbol}",
                status="REJECTED_BY_SAFETY_GATE",
                venue=self.venue_name,
                rejection_reasons=[str(exc)],
            )

        # Only reached if all safety gates pass (Phase 7+ with verified certificate)
        return self._submit_live_order(request)

    @abstractmethod
    def _submit_live_order(self, request: LiveOrderRequest) -> LiveOrderResult:
        """Submits real signed order to external exchange API. Implemented in concrete subclasses."""
        pass
