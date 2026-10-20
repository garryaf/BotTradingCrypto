"""Hermes Multi-Agent Orchestrator — ROADMAP TASK-3.3/3.4.

Isolation (TASK-3.4): this module only ever writes to agent_runs,
llm_requests and trading_signals (status PENDING). It has no access to
paper_orders/positions/balances and must stay that way — order execution
is the Risk Gate + Paper Broker's job (Fase 4), not the agent's.
"""
import asyncio
import json
import logging
import time
from datetime import datetime, timedelta, timezone
from decimal import Decimal

import httpx
from pydantic import ValidationError
from sqlmodel import select

from ..db import async_session_factory
from ..gateway.client import GatewayError, chat_completion_with_fallback
from ..models import AgentRun, LLMRequest, MarketOHLCV, Token, TradingSignal
from .indicators import ema, rsi
from .schemas import RegimeResult, SafetyResult, SignalResult
from .skills import load_skill_prompt

logger = logging.getLogger("agents.hermes")

SYMBOLS = ["BTCUSDT", "ETHUSDT", "SOLUSDT"]
CYCLE_INTERVAL_SEC = 300
CONFIDENCE_THRESHOLD = 0.75
MIN_CANDLES = 20


async def build_market_context(session, token: Token) -> dict | None:
    rows = (
        await session.exec(
            select(MarketOHLCV)
            .where(MarketOHLCV.token_id == token.id, MarketOHLCV.interval == "M1")
            .order_by(MarketOHLCV.bucket_time.asc())
            .limit(60)
        )
    ).all()
    closes = [float(r.close) for r in rows]
    if len(closes) < MIN_CANDLES:
        return None
    return {
        "symbol": f"{token.symbol}USDT",
        "recent_closes": closes[-30:],
        "ema20": round(ema(closes, 20), 6),
        "ema50": round(ema(closes, 50), 6),
        "rsi14": round(rsi(closes, 14), 2),
        "last_price": closes[-1],
    }


async def _call_skill(session, client, agent_run_id, skill_name: str, context: dict, schema):
    system_prompt = load_skill_prompt(skill_name)
    user_prompt = json.dumps(context, default=str)
    provider, model, content, usage, latency_ms = await chat_completion_with_fallback(
        system_prompt, user_prompt, client=client
    )

    status_code, parsed, response_json = 200, None, {}
    try:
        response_json = json.loads(content)
        parsed = schema.model_validate(response_json)
    except (json.JSONDecodeError, ValidationError):
        status_code = 422

    session.add(
        LLMRequest(
            agent_run_id=agent_run_id,
            provider=provider,
            model_name=model,
            prompt_tokens=usage.get("prompt_tokens", 0),
            completion_tokens=usage.get("completion_tokens", 0),
            latency_ms=Decimal(str(latency_ms)),
            status_code=status_code,
            request_prompt_summary={"skill": skill_name, "context": context},
            response_json=response_json if isinstance(response_json, dict) else {"raw": content},
        )
    )
    await session.commit()

    if parsed is None:
        raise GatewayError(f"{skill_name}: model output failed schema validation")
    return parsed


async def run_hermes_cycle(session, client: httpx.AsyncClient, symbol: str) -> TradingSignal | None:
    token = (await session.exec(select(Token).where(Token.address == symbol))).first()
    if not token:
        return None
    ctx = await build_market_context(session, token)
    if ctx is None:
        return None

    run = AgentRun(agent_name="HERMES", task_type="SIGNAL_SYNTHESIS", status="STARTED")
    session.add(run)
    await session.commit()
    await session.refresh(run)
    start = time.monotonic()

    try:
        regime: RegimeResult = await _call_skill(
            session, client, run.id, "market-regime-detection", ctx, RegimeResult
        )
        safety: SafetyResult = await _call_skill(
            session, client, run.id, "token-and-contract-safety", {"symbol": ctx["symbol"]}, SafetyResult
        )
        if safety.verdict != "APPROVED":
            run.status, run.execution_time_ms = "SUCCESS", Decimal(str(round((time.monotonic() - start) * 1000, 2)))
            await session.commit()
            return None

        signal: SignalResult = await _call_skill(
            session,
            client,
            run.id,
            "signal-scoring-hybrid",
            {**ctx, "regime": regime.model_dump()},
            SignalResult,
        )
    except GatewayError as exc:
        logger.warning("Hermes cycle failed for %s: %s", symbol, exc)
        run.status = "FAILED"
        await session.commit()
        return None

    run.status, run.execution_time_ms = "SUCCESS", Decimal(str(round((time.monotonic() - start) * 1000, 2)))
    await session.commit()

    if signal.action not in ("BUY", "SELL") or signal.confidence_score < CONFIDENCE_THRESHOLD:
        return None

    trading_signal = TradingSignal(
        agent_run_id=run.id,
        token_id=token.id,
        symbol=ctx["symbol"],
        action=signal.action,
        target_entry_price=Decimal(str(signal.entry_price)),
        suggested_stop_loss=Decimal(str(signal.stop_loss)),
        suggested_take_profit_1=Decimal(str(signal.take_profit_1)),
        suggested_take_profit_2=Decimal(str(signal.take_profit_2)),
        confidence_score=Decimal(str(round(signal.confidence_score, 3))),
        estimated_winrate_pct=Decimal(str(signal.estimated_winrate_pct)),
        rationale=signal.rationale,
        expires_at=datetime.now(timezone.utc) + timedelta(minutes=5),
    )
    session.add(trading_signal)
    await session.commit()
    await session.refresh(trading_signal)
    return trading_signal


def gateway_is_configured() -> bool:
    from ..gateway.client import _is_configured
    from ..config import settings

    return (settings.openrouter_base_url and _is_configured(settings.openrouter_api_key)) or (
        settings.nineroute_base_url and _is_configured(settings.nineroute_api_key)
    )


async def run_hermes_loop() -> None:
    if not gateway_is_configured():
        logger.warning("Hermes loop idle: no AI Model Gateway provider configured (OPENROUTER_API_KEY / NINEROUTE_API_KEY)")
        return
    from ..risk.engine import is_paused

    async with httpx.AsyncClient() as client:
        while True:
            async with async_session_factory() as session:
                if not await is_paused(session):
                    for symbol in SYMBOLS:
                        await run_hermes_cycle(session, client, symbol)
            await asyncio.sleep(CYCLE_INTERVAL_SEC)
