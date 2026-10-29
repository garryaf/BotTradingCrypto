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
from ..models import MarketSnapshot, Position, SystemEvent, Token, Wallet, WalletObservation
from .common import is_stale, log_dlq

logger = logging.getLogger("ingestion.solana")

POLL_INTERVAL_SEC = 15
SOL_MINT = "So11111111111111111111111111111111111111112"
DEX_PROGRAM_HINTS = {"Raydium": "RAYDIUM", "Orca": "ORCA", "Jupiter": "JUPITER"}
TOKEN_PROGRAM_ID = "TokenkegQfeZyiNwAJbNbGKPFXCWuBvf9Ss623VQ5DA"  # classic SPL Token program
RAYDIUM_AMM_PROGRAM_ID = "675kPX9MHTjS2zt1qfr1NYHuzeLXfQM9H24wFSUt1Mp8"
JUPITER_V6_PROGRAM_ID = "JUP6LkbZbjS1jKKwapdHNy74zcZ3tLUZoi5QNyVTaV4"
KNOWN_PROGRAM_IDS = {
    "11111111111111111111111111111111",
    "TokenkegQfeZyiNwAJbNbGKPFXCWuBvf9Ss623VQ5DA",
    "TokenzQdBNbLqP5VEhdkAS6EPFLC1PHnBqCXEpPxuEb",
    "ATokenGPvbdGVxr1b2hvZbsiqW5xWH25efTNsLJA8knL",
    "ComputeBudget111111111111111111111111111111",
    "675kPX9MHTjS2zt1qfr1NYHuzeLXfQM9H24wFSUt1Mp8",
    "JUP6LkbZbjS1jKKwapdHNy74zcZ3tLUZoi5QNyVTaV4",
    "whirLbMiicVdio4qvUfM5KAg6Ct8VwpYzGff3uctyCc",
}
DEXSCREENER_TOKENS_URL = "https://api.dexscreener.com/tokens/v1/solana"  # BLOCKCHAIN_DATA_SOURCES.md §2
MONITORED_STATUSES = ("APPROVED", "ACTIVE_MONITORED")
# Archived wallets are not polled ("Jangan Pantau Transaksi", WALLET_DISCOVERY_FLOWCHART.mmd).
POLLED_WALLETS = select(Wallet).where(Wallet.chain == "solana", Wallet.status != "ARCHIVED")


async def _rpc(client: httpx.AsyncClient, method: str, params: list, max_retries: int = 3, initial_delay: float = 0.05) -> dict:
    delay = initial_delay
    for attempt in range(max_retries):
        res = await client.post(settings.solana_rpc_url, json={"jsonrpc": "2.0", "id": 1, "method": method, "params": params})
        if res.status_code == 429 and attempt < max_retries - 1:
            retry_after = res.headers.get("Retry-After")
            wait_time = float(retry_after) if retry_after and retry_after.isdigit() else delay
            logger.warning("Solana RPC 429 rate limited, backing off %.2fs (attempt %d/%d)", wait_time, attempt + 1, max_retries)
            await asyncio.sleep(wait_time)
            delay *= 2
            continue
        res.raise_for_status()
        body = res.json()
        if "error" in body:
            raise RuntimeError(body["error"])
        return body["result"]
    res.raise_for_status()
    return res.json()["result"]


async def _get_or_create_token(session: AsyncSession, mint: str, decimals: int = 9) -> Token:
    token = (await session.exec(select(Token).where(Token.address == mint))).first()
    if token:
        return token
    # Fail-closed: a new SPL token is unsafe until _verify_mint_authorities reads its mint account
    # (the model default "revoked" let copy-trade's token-safety gate pass blind, F-19).
    token = Token(address=mint, chain="solana", symbol=mint[:4], decimals=decimals,
                  freeze_authority_revoked=False, mint_authority_revoked=False)
    session.add(token)
    await session.commit()
    await session.refresh(token)
    return token


async def _verify_mint_authorities(client: httpx.AsyncClient, token: Token) -> None:
    """Sets the copy-trade token-safety flags from the mint account itself, every time (rows created
    before F-19 defaulted to "revoked" unverified). Fail-closed: an RPC error or a non-mint account
    leaves the token unsafe."""
    try:
        account = (await _rpc(client, "getAccountInfo", [token.address, {"encoding": "jsonParsed"}]))["value"]
        parsed = account["data"]["parsed"] if account and account["owner"] == TOKEN_PROGRAM_ID else None
        info = parsed["info"] if parsed and parsed["type"] == "mint" else None
    except (httpx.HTTPError, RuntimeError, KeyError, TypeError, ValueError) as exc:
        logger.warning("mint check failed for %s: %s", token.address, exc)
        info = None
    # shortcut: Token-2022 mints count as unsafe (their extensions, e.g. permanentDelegate or
    # transferHook, aren't inspected); support them by checking the parsed extensions.
    token.mint_authority_revoked = info is not None and info.get("mintAuthority") is None
    token.freeze_authority_revoked = info is not None and info.get("freezeAuthority") is None


async def _refresh_market(client: httpx.AsyncClient, session: AsyncSession, token: Token) -> MarketSnapshot | None:
    """USD price, pool liquidity and 24h volume from the token's most liquid DEXScreener pair, saved as a
    market snapshot so the risk engine can judge the copy-trade. None when there is no usable pair."""
    try:
        res = await client.get(f"{DEXSCREENER_TOKENS_URL}/{token.address}", timeout=10)
        res.raise_for_status()
        data = res.json()
        pairs = [p for p in data if (p.get("baseToken") or {}).get("address") == token.address] if isinstance(data, list) else []
        best = max(pairs, key=lambda p: (p.get("liquidity") or {}).get("usd") or 0, default=None)
        price = Decimal(best["priceUsd"]) if best and best.get("priceUsd") else None
    except (httpx.HTTPError, ValueError, KeyError, TypeError, AttributeError, ArithmeticError) as exc:
        logger.warning("DEXScreener lookup failed for %s: %s", token.address, exc)
        return None
    if price is None or price <= 0:
        return None
    liquidity = Decimal(str((best.get("liquidity") or {}).get("usd") or 0))
    token.pool_liquidity_usd = liquidity
    volume_24h = Decimal(str((best.get("volume") or {}).get("h24") or 0))

    # AMM synthetic quote model (F-16): Raydium/Orca standard 0.30% swap fee + size impact.
    # Impact approximation: standard $100 order against pool depth. If pool has 0 liquidity, bid/ask remain None (fail-closed).
    if liquidity > 0:
        base_fee = settings.dex_pool_base_fee_pct
        impact = min(Decimal("0.0200"), Decimal("100.00") / liquidity)
        half_spread = base_fee + impact
        bid = (price * (Decimal(1) - half_spread)).quantize(Decimal("0.000001"))
        ask = (price * (Decimal(1) + half_spread)).quantize(Decimal("0.000001"))
        spread = ((ask - bid) / price * Decimal(100)).quantize(Decimal("0.0001"))
    else:
        bid, ask, spread = None, None, None

    snapshot = MarketSnapshot(
        token_id=token.id,
        price_usd=price,
        volume_24h_usd=volume_24h,
        pool_liquidity_usd=liquidity,
        bid_price=bid,
        ask_price=ask,
        spread_pct=spread,
        source="DEXSCREENER",
        snapshot_time=datetime.now(timezone.utc),
    )
    session.add(snapshot)
    await session.commit()
    return snapshot


def _token_delta(balances: list, owner: str) -> dict[str, Decimal]:
    """mint -> signed ui-amount delta for this owner, from pre/post token balance lists."""
    out: dict[str, Decimal] = {}
    for b in balances:
        if b.get("owner") != owner:
            continue
        out[b["mint"]] = out.get(b["mint"], Decimal(0)) + Decimal(b["uiTokenAmount"]["uiAmountString"] or "0")
    return out


async def _normalize(
    client: httpx.AsyncClient, session: AsyncSession, wallet: Wallet, sig: str, tx: dict, fresh: bool
) -> None:
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
        return

    # Copy only a fresh swap of an operator-approved wallet (BR-01, COPY_TRADING_FLOWCHART.mmd); older
    # history is kept for scoring only.
    if fresh and wallet.status in MONITORED_STATUSES and action in ("BUY", "SELL"):
        target_token = token_out if action == "BUY" else token_in
        if target_token:
            # The old price was the swap's SOL/token ratio (or a hardcoded $100), used as a USD entry.
            price_usd = Decimal(0)
            if action == "BUY":  # SELLs aren't mirrored (copy_trade.py): don't spend RPC/API calls on them
                await _verify_mint_authorities(client, target_token)
                snapshot = await _refresh_market(client, session, target_token)
                price_usd = snapshot.price_usd if snapshot else Decimal(0)  # 0 -> rejected as INVALID_PRICE
            try:
                from ..agents.copy_trade import create_copy_trade_signal
                await create_copy_trade_signal(session, wallet, target_token, action, price_usd)
            except Exception as exc:
                logger.warning("Copy-trade signal creation failed: %s", exc)


async def _poll_wallet(client: httpx.AsyncClient, session: AsyncSession, wallet: Wallet, max_signatures: int = 50) -> None:
    try:
        sigs = await _rpc(client, "getSignaturesForAddress", [wallet.address, {"limit": max_signatures}])
    except (httpx.HTTPError, RuntimeError) as exc:
        await log_dlq(session, "SOLANA_RPC", "PARSE_ERROR", wallet.address, {"error": str(exc)})
        return

    for entry in sigs:
        sig = entry["signature"]
        exists = (await session.exec(select(WalletObservation).where(WalletObservation.tx_signature == sig))).first()
        if exists:
            continue
        # An older tx is history the scorer needs, not an error: it used to be DLQ'd and never recorded,
        # so a new wallet could never be scored and the same signatures were DLQ'd again every poll (F-28).
        # shortcut: only the 10 newest signatures per poll are read; paginate with `before` to backfill
        # the 30-day history WALLET_DISCOVERY_FLOWCHART.mmd asks for.
        fresh = not (entry.get("blockTime") and is_stale(datetime.fromtimestamp(entry["blockTime"], tz=timezone.utc)))
        try:
            tx = await _rpc(
                client,
                "getTransaction",
                [sig, {"encoding": "jsonParsed", "maxSupportedTransactionVersion": 0}],
            )
            if tx is None:
                raise RuntimeError("tx not found (not yet finalized)")
            await _normalize(client, session, wallet, sig, tx, fresh)
        except (httpx.HTTPError, RuntimeError, KeyError) as exc:
            await log_dlq(session, "SOLANA_RPC", "PARSE_ERROR", sig, {"error": str(exc)})


async def refresh_open_spl_positions(client: httpx.AsyncClient, session: AsyncSession) -> list[MarketSnapshot]:
    """Fetch fresh DEX prices for tokens of all open Solana positions so the risk engine can evaluate TP/SL."""
    positions = (await session.exec(select(Position).where(Position.status.in_(("OPEN", "PARTIALLY_CLOSED"))))).all()
    if not positions:
        return []
    token_ids = {pos.token_id for pos in positions}
    snapshots = []
    for tid in token_ids:
        tok = await session.get(Token, tid)
        if tok and tok.chain == "solana":
            snap = await _refresh_market(client, session, tok)
            if snap:
                snapshots.append(snap)
    return snapshots


async def crawl_candidate_wallets(client: httpx.AsyncClient, session: AsyncSession, limit: int = 10) -> list[Wallet]:
    """Automated crawler discovering candidate Solana trader wallets from DEX swap activity
    (WALLET_DISCOVERY_FLOWCHART.mmd). New wallets start in DISCOVERED status for scoring."""
    discovered: list[Wallet] = []
    # Query Raydium and Jupiter program accounts for recent swap transactions
    for program_id in (RAYDIUM_AMM_PROGRAM_ID, JUPITER_V6_PROGRAM_ID):
        if len(discovered) >= limit:
            break
        try:
            sigs = await _rpc(client, "getSignaturesForAddress", [program_id, {"limit": limit * 2}])
        except Exception as exc:
            logger.warning("Crawler RPC getSignaturesForAddress failed for %s: %s", program_id, exc)
            continue

        for entry in sigs:
            if len(discovered) >= limit:
                break
            sig = entry.get("signature")
            if not sig:
                continue
            try:
                tx = await _rpc(
                    client,
                    "getTransaction",
                    [sig, {"encoding": "jsonParsed", "maxSupportedTransactionVersion": 0}],
                )
                if not tx or not tx.get("transaction"):
                    continue
                message = tx["transaction"].get("message", {})
                account_keys = message.get("accountKeys", [])

                trader_pubkey = None
                for key_entry in account_keys:
                    if isinstance(key_entry, dict) and key_entry.get("signer"):
                        candidate = key_entry.get("pubkey")
                        if candidate and candidate not in KNOWN_PROGRAM_IDS:
                            trader_pubkey = candidate
                            break
                    elif isinstance(key_entry, str) and key_entry not in KNOWN_PROGRAM_IDS:
                        trader_pubkey = key_entry
                        break

                if not trader_pubkey or len(trader_pubkey) < 32 or len(trader_pubkey) > 44:
                    continue

                exists = (await session.exec(select(Wallet).where(Wallet.address == trader_pubkey))).first()
                if not exists and not any(w.address == trader_pubkey for w in discovered):
                    new_wallet = Wallet(address=trader_pubkey, chain="solana", status="DISCOVERED")
                    session.add(new_wallet)
                    session.add(
                        SystemEvent(
                            event_type="WALLET_DISCOVERED",
                            message=f"Automated crawler discovered candidate wallet {trader_pubkey}",
                        )
                    )
                    await session.commit()
                    await session.refresh(new_wallet)
                    discovered.append(new_wallet)
                    logger.info("Crawler discovered new wallet: %s", trader_pubkey)
            except Exception as exc:
                logger.debug("Failed inspecting transaction %s in crawler: %s", sig, exc)
                continue

    return discovered


async def run_solana_ingestion() -> None:
    cycle = 0
    async with httpx.AsyncClient(timeout=15) as client:
        while True:
            async with async_session_factory() as session:
                # 1. Poll approved & monitored wallets for new swaps
                wallets = (await session.exec(POLLED_WALLETS)).all()
                for wallet in wallets:
                    await _poll_wallet(client, session, wallet)

                # 2. Continuous price poller for open SPL positions (TP/SL monitoring)
                try:
                    await refresh_open_spl_positions(client, session)
                except Exception as exc:
                    logger.warning("Failed refreshing open SPL positions: %s", exc)

                # 3. Automated wallet discovery crawler (every 20 cycles = ~5 minutes)
                cycle += 1
                if cycle % 20 == 0:
                    try:
                        await crawl_candidate_wallets(client, session, limit=5)
                    except Exception as exc:
                        logger.warning("Automated wallet crawler error: %s", exc)

            await asyncio.sleep(POLL_INTERVAL_SEC)
