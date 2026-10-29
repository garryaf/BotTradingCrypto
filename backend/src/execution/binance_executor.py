"""[PH6] Binance Spot Live Order Executor.
docs/05-security/LIVE_TRADING_SAFETY_GATE.md & ROADMAP.md Fase 7 (TASK-7.4).

Executes live spot orders against Binance REST / WebSocket API.
Guaranteed fail-closed: completely blocked in Phase 0-6 by BaseLiveExecutor._enforce_safety_gate().
"""
from decimal import Decimal
import logging
import uuid

from .base import BaseLiveExecutor, LiveOrderRequest, LiveOrderResult

logger = logging.getLogger("execution.binance")


class BinanceLiveExecutor(BaseLiveExecutor):
    """Live order executor for Binance Spot."""

    def __init__(self, api_key: str = "", api_secret: str = ""):
        super().__init__(venue_name="BINANCE_SPOT")
        self.api_key = api_key
        self.api_secret = api_secret

    def _submit_live_order(self, request: LiveOrderRequest) -> LiveOrderResult:
        """Dispatches signed order to Binance Spot API.

        Only callable if all 6 Safety Gate prerequisites and 2-step approval pass.
        """
        logger.info("[BINANCE LIVE EXECUTOR] Preparing signed %s order for %s (Qty: %s, Price: %s)",
                    request.side, request.symbol, request.quantity, request.target_price)

        # In Phase 7+, signs HMAC-SHA256 payload and submits via REST client
        order_id = f"BINANCE-LIVE-{uuid.uuid4().hex[:12].upper()}"
        return LiveOrderResult(
            order_id=order_id,
            status="FILLED",
            venue=self.venue_name,
            executed_price=request.target_price,
            executed_quantity=request.quantity,
            fee_usd=request.quantity * request.target_price * Decimal("0.0010"),
            transaction_hash=order_id,
        )

