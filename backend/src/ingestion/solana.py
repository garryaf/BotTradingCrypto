"""Solana wallet ingestion — ROADMAP.md TASK-2.2/2.3.

ponytail: action/amount detection uses a simple balance-delta heuristic
(largest SPL token delta = the swap side, native SOL delta = the other side).
It does not decode Raydium/Orca/Jupiter instructions directly. Good enough to
populate wallet_observations for Fase 2; upgrade to full instruction decoding
if Wallet Discovery scoring (Q-05) needs per-DEX precision.
"""
import asyncio
import logging
from datetime import datetime, timezone
from decimal import Decimal

import httpx
from sqlalchemy.exc import IntegrityError
from sqlmodel import select
from sqlmodel.ext.asyncio.session import AsyncSession

from ..config import settings
from ..db import async_session_factory
from ..models import Token, Wallet, WalletObservation
from .common import is_stale, log_dlq

logger = logging.getLogger("ingestion.solana")

POLL_INTERVAL_SEC = 15
SOL_MINT = "So11111111111111111111111111111111111111112"
DEX_PROGRAM_HINTS = {"Raydium": "RAYDIUM", "Orca": "ORCA", "Jupiter": "JUPITER"}


async def _rpc(client: httpx.AsyncClient, method: str, params: list) -> dict:
    res = await client.post(settings.solana_rpc_url, json={"jsonrpc": "2.0", "id": 1, "method": method, "params": params})
    res.raise_for_status()
    body = res.json()
    if "error" in body:
        raise RuntimeError(body["error"])
    return body["result"]


async def _get_or_create_token(session: AsyncSession, mint: str, decimals: int = 9) -> Token:
    token = (await session.exec(select(Token).where(Token.address == mint))).first()
    if token:
        return token
    token = Token(address=mint, chain="solana", symbol=mint[:4], decimals=decimals)
    session.add(token)
    await session.commit()
    await session.refresh(token)
    return token


def _token_delta(balances: list, owner: str) -> dict[str, Decimal]:
    """mint -> signed ui-amount delta for this owner, from pre/post token balance lists."""
    out: dict[str, Decimal] = {}
    for b in balances:
        if b.get("owner") != owner:
            continue
        out[b["mint"]] = out.get(b["mint"], Decimal(0)) + Decimal(b["uiTokenAmount"]["uiAmountString"] or "0")
    return out


async def _normalize(session: AsyncSession, wallet: Wallet, sig: str, tx: dict) -> None:
    meta = tx["meta"]
    account_keys = [k["pubkey"] if isinstance(k, dict) else k for k in tx["transaction"]["message"]["accountKeys"]]
    try:
        idx = account_keys.index(wallet.address)
        sol_delta = Decimal(meta["postBalances"][idx] - meta["preBalances"][idx]) / Decimal(10**9)
    except ValueError:
        sol_delta = Decimal(0)

    pre = _token_delta(meta.get("preTokenBalances", []), wallet.address)
    post = _token_delta(meta.get("postTokenBalances", []), wallet.address)
    mint_deltas = {m: post.get(m, Decimal(0)) - pre.get(m, Decimal(0)) for m in set(pre) | set(post)}
    mint_deltas = {m: d for m, d in mint_deltas.items() if d != 0}

    dex_protocol = next(
        (tag for name, tag in DEX_PROGRAM_HINTS.items() if any(name in log for log in meta.get("logMessages", []))),
        None,
    )

    if mint_deltas:
        mint, delta = max(mint_deltas.items(), key=lambda kv: abs(kv[1]))
        token = await _get_or_create_token(session, mint)
        if delta > 0:
            action, token_out, amount_out = "BUY", token, delta
            token_in, amount_in = (None, Decimal(0)) if sol_delta >= 0 else (await _get_or_create_token(session, SOL_MINT), -sol_delta)
        else:
            action, token_in, amount_in = "SELL", token, -delta
            token_out, amount_out = (None, Decimal(0)) if sol_delta <= 0 else (await _get_or_create_token(session, SOL_MINT), sol_delta)
    elif sol_delta != 0:
        sol_token = await _get_or_create_token(session, SOL_MINT)
        if sol_delta > 0:
            action, token_in, amount_in, token_out, amount_out = "TRANSFER_IN", sol_token, sol_delta, None, Decimal(0)
        else:
            action, token_in, amount_in, token_out, amount_out = "TRANSFER_OUT", None, Decimal(0), sol_token, -sol_delta
    else:
        action, token_in, amount_in, token_out, amount_out = "TRANSFER_IN", None, Decimal(0), None, Decimal(0)

    session.add(
        WalletObservation(
            wallet_id=wallet.id,
            tx_signature=sig,
            chain="solana",
            dex_protocol=dex_protocol,
            action=action,
            token_in_id=token_in.id if token_in else None,
            token_out_id=token_out.id if token_out else None,
            amount_in=amount_in,
            amount_out=amount_out,
            network_fee_native=Decimal(meta.get("fee", 5000)) / Decimal(10**9),
            finality_status="confirmed",
            block_time=datetime.fromtimestamp(tx["blockTime"], tz=timezone.utc) if tx.get("blockTime") else datetime.now(timezone.utc),
            raw_payload={"slot": tx.get("slot")},
        )
    )
    try:
        await session.commit()
    except IntegrityError:
        await session.rollback()
        await log_dlq(session, "SOLANA_RPC", "DUPLICATE_SIGNATURE", sig, {"wallet": wallet.address})


async def _poll_wallet(client: httpx.AsyncClient, session: AsyncSession, wallet: Wallet) -> None:
    try:
        sigs = await _rpc(client, "getSignaturesForAddress", [wallet.address, {"limit": 10}])
    except (httpx.HTTPError, RuntimeError) as exc:
        await log_dlq(session, "SOLANA_RPC", "PARSE_ERROR", wallet.address, {"error": str(exc)})
        return

    for entry in sigs:
        sig = entry["signature"]
        exists = (await session.exec(select(WalletObservation).where(WalletObservation.tx_signature == sig))).first()
        if exists:
            continue
        if entry.get("blockTime") and is_stale(datetime.fromtimestamp(entry["blockTime"], tz=timezone.utc)):
            await log_dlq(session, "SOLANA_RPC", "STALE_DATA", sig, {"wallet": wallet.address})
            continue
        try:
            tx = await _rpc(
                client,
                "getTransaction",
                [sig, {"encoding": "jsonParsed", "maxSupportedTransactionVersion": 0}],
            )
            if tx is None:
                raise RuntimeError("tx not found (not yet finalized)")
            await _normalize(session, wallet, sig, tx)
        except (httpx.HTTPError, RuntimeError, KeyError) as exc:
            await log_dlq(session, "SOLANA_RPC", "PARSE_ERROR", sig, {"error": str(exc)})


async def run_solana_ingestion() -> None:
    async with httpx.AsyncClient(timeout=15) as client:
        while True:
            async with async_session_factory() as session:
                wallets = (await session.exec(select(Wallet).where(Wallet.chain == "solana"))).all()
                for wallet in wallets:
                    await _poll_wallet(client, session, wallet)
            await asyncio.sleep(POLL_INTERVAL_SEC)
