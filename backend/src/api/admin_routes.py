from datetime import datetime, timedelta, timezone
from typing import Literal
from uuid import UUID

import httpx
from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field
from sqlalchemy import func
from sqlalchemy.exc import IntegrityError
from sqlmodel import select
from sqlmodel.ext.asyncio.session import AsyncSession

from ..auth.dependencies import get_current_admin
from ..db import get_session
from ..models import (
    AgentRun,
    BinanceCredential,
    IngestionError,
    LLMRequest,
    RiskCheck,
    SystemEvent,
    TradingSignal,
    User,
    Wallet,
)

router = APIRouter(prefix="/api/v1/admin")

VALID_ROLES = {"user", "admin"}


class UserPatch(BaseModel):
    role: str | None = None
    is_active: bool | None = None


class WalletIn(BaseModel):
    address: str = Field(pattern=r"^[1-9A-HJ-NP-Za-km-z]{32,44}$")  # Solana base58 public key


class WalletDecision(BaseModel):
    status: Literal["ACTIVE_MONITORED", "ARCHIVED"]


WALLET_EVENTS = {"ACTIVE_MONITORED": "WALLET_APPROVED", "ARCHIVED": "WALLET_ARCHIVED"}


@router.get("/users")
async def list_users(admin: User = Depends(get_current_admin), session: AsyncSession = Depends(get_session)):
    users = (await session.exec(select(User).order_by(User.created_at))).all()
    configured_ids = set((await session.exec(select(BinanceCredential.user_id))).all())
    return [
        {
            "id": str(u.id),
            "email": u.email,
            "role": u.role,
            "is_active": u.is_active,
            "binance_configured": u.id in configured_ids,
            "created_at": u.created_at,
        }
        for u in users
    ]


@router.patch("/users/{user_id}")
async def update_user(
    user_id: UUID,
    body: UserPatch,
    admin: User = Depends(get_current_admin),
    session: AsyncSession = Depends(get_session),
):
    target = await session.get(User, user_id)
    if not target:
        raise HTTPException(status_code=404, detail="User not found")
    if str(target.id) == str(admin.id) and (body.role == "user" or body.is_active is False):
        raise HTTPException(status_code=400, detail="Can't demote or disable your own account")

    if body.role is not None:
        if body.role not in VALID_ROLES:
            raise HTTPException(status_code=422, detail=f"role must be one of {VALID_ROLES}")
        target.role = body.role
    if body.is_active is not None:
        target.is_active = body.is_active

    await session.commit()
    return {"id": str(target.id), "email": target.email, "role": target.role, "is_active": target.is_active}


@router.post("/wallets", status_code=201)
async def add_wallet(body: WalletIn, admin: User = Depends(get_current_admin), session: AsyncSession = Depends(get_session)):
    """Candidate intake (WALLET_DISCOVERY_FLOWCHART): the operator submits an address, it starts DISCOVERED,
    ingestion collects its swaps, and the scoring loop promotes it to PENDING_REVIEW at score >= 70."""
    session.add(Wallet(address=body.address, chain="solana"))
    try:
        await session.commit()
    except IntegrityError:  # unique address; also covers two admins adding it at once
        await session.rollback()
        raise HTTPException(status_code=409, detail="Wallet already registered")
    return {"address": body.address, "status": "DISCOVERED"}


@router.post("/wallets/crawl")
async def trigger_wallet_crawl(
    limit: int = 10,
    admin: User = Depends(get_current_admin),
    session: AsyncSession = Depends(get_session),
):
    """Trigger automated crawler to discover candidate wallets from Solana DEX swaps (WALLET_DISCOVERY_FLOWCHART)."""
    from ..ingestion.solana import crawl_candidate_wallets

    async with httpx.AsyncClient(timeout=15) as client:
        discovered = await crawl_candidate_wallets(client, session, limit=limit)
    return {
        "discovered_count": len(discovered),
        "wallets": [{"address": w.address, "status": w.status} for w in discovered],
    }


@router.patch("/wallets/{address}")
async def decide_wallet(
    address: str,
    body: WalletDecision,
    admin: User = Depends(get_current_admin),
    session: AsyncSession = Depends(get_session),
):
    """Human-in-the-loop decision (WALLET_DISCOVERY_FLOWCHART): approve a scored PENDING_REVIEW wallet for
    copy-trading, or archive any wallet to stop polling it. Wallets are shared, so this is admin-only."""
    wallet = (await session.exec(select(Wallet).where(Wallet.address == address))).first()
    if not wallet:
        raise HTTPException(status_code=404, detail="Wallet not found")
    now = datetime.now(timezone.utc)
    if body.status == "ACTIVE_MONITORED" and wallet.status != "ACTIVE_MONITORED":
        if wallet.status != "PENDING_REVIEW":  # the score gate can't be skipped
            raise HTTPException(status_code=409, detail=f"Only PENDING_REVIEW wallets can be approved (is {wallet.status})")
        wallet.approved_at = now
    if wallet.status != body.status:
        wallet.status, wallet.updated_at = body.status, now
        session.add(SystemEvent(event_type=WALLET_EVENTS[body.status], message=f"{admin.email}: {address}"))
        await session.commit()
    return {"address": wallet.address, "status": wallet.status, "approved_at": wallet.approved_at}


@router.get("/metrics")
async def metrics(admin: User = Depends(get_current_admin), session: AsyncSession = Depends(get_session)):
    """Last-24h counters straight from existing tables (GAP-14): AI usage/cost and pipeline health."""
    since = datetime.now(timezone.utc) - timedelta(hours=24)

    async def counts(column, ts_column) -> dict:
        rows = (await session.exec(select(column, func.count()).where(ts_column >= since).group_by(column))).all()
        return dict(rows)

    requests, tokens, cost, avg_latency = (
        await session.exec(
            select(
                func.count(LLMRequest.id),
                func.coalesce(func.sum(LLMRequest.prompt_tokens + LLMRequest.completion_tokens), 0),
                func.coalesce(func.sum(LLMRequest.cost_usd), 0),
                func.avg(LLMRequest.latency_ms),
            ).where(LLMRequest.requested_at >= since)
        )
    ).one()
    llm_errors = (
        await session.exec(
            select(func.count(LLMRequest.id)).where(LLMRequest.requested_at >= since, LLMRequest.status_code != 200)
        )
    ).one()
    critical_events = (
        await session.exec(
            select(func.count(SystemEvent.id)).where(SystemEvent.created_at >= since, SystemEvent.severity == "CRITICAL")
        )
    ).one()
    risk = await counts(RiskCheck.passed, RiskCheck.evaluated_at)
    return {
        "window_hours": 24,
        "llm": {
            "requests": requests,
            "errors": llm_errors,
            "tokens": int(tokens),
            "cost_usd": cost,
            "avg_latency_ms": round(float(avg_latency), 2) if avg_latency is not None else None,
        },
        "agent_runs": await counts(AgentRun.status, AgentRun.created_at),
        "signals": await counts(TradingSignal.status, TradingSignal.generated_at),
        "risk_checks": {"passed": risk.get(True, 0), "rejected": risk.get(False, 0)},
        "ingestion_errors": await counts(IngestionError.reason, IngestionError.occurred_at),
        "critical_events": critical_events,
    }
