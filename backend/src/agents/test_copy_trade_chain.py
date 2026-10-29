"""Copy-trade chain end-to-end on synthetic data (P1-1, F-16): the operator adds a candidate wallet ->
ingestion records its swap history -> scoring promotes it to PENDING_REVIEW -> the operator approves it
-> a fresh BUY swap becomes a TradingSignal(PENDING) -> the risk engine judges that signal.

Every step runs the real code path: the admin API over ASGI, solana._poll_wallet with the Solana RPC
and DEXScreener mocked at the HTTP layer (httpx.MockTransport, nothing leaves the machine),
wallet_scorer.update_wallet_scores, and risk.engine._dispatch_pending. All rows are synthetic.

Needs DATABASE_URL on an empty migrated DB (the first registered user becomes admin) plus the JWT and
Fernet env vars; see scripts/run_integration_tests.sh. Skips cleanly without DATABASE_URL.
"""
import asyncio
import json
import os
import random
import time
from decimal import Decimal

import httpx

B58 = "123456789ABCDEFGHJKLMNPQRSTUVWXYZabcdefghijkmnopqrstuvwxyz"
TOKEN_PROGRAM_ID = "TokenkegQfeZyiNwAJbNbGKPFXCWuBvf9Ss623VQ5DA"


def _address(tag: str) -> str:
    """Synthetic base58 address, recognisable by its prefix."""
    return tag + "".join(random.choices(B58, k=44 - len(tag)))


def _swap_tx(wallet: str, mint: str, sol_lamports: int, tokens_before: str, tokens_after: str, block_time: int) -> dict:
    """Minimal jsonParsed getTransaction result: the wallet's SOL and token balance changes."""
    return {
        "slot": 1,
        "blockTime": block_time,
        "meta": {
            "fee": 5000,
            "preBalances": [50_000_000_000],
            "postBalances": [50_000_000_000 + sol_lamports],
            "preTokenBalances": [{"owner": wallet, "mint": mint, "uiTokenAmount": {"uiAmountString": tokens_before}}],
            "postTokenBalances": [{"owner": wallet, "mint": mint, "uiTokenAmount": {"uiAmountString": tokens_after}}],
            "logMessages": ["Program log: Raydium swap"],
        },
        "transaction": {"message": {"accountKeys": [{"pubkey": wallet}]}},
    }


class FakeChain:
    """Answers the Solana JSON-RPC and DEXScreener calls _poll_wallet makes, and records them."""

    def __init__(self):
        self.signatures: dict[str, list] = {}  # wallet -> [{signature, blockTime}], newest first
        self.txs: dict[str, dict] = {}
        self.mints: dict[str, dict] = {}  # mint -> parsed mint info
        self.pairs: dict[str, list] = {}  # mint -> DEXScreener pairs
        self.calls: list[tuple[str, str]] = []

    def handler(self, request: httpx.Request) -> httpx.Response:
        if request.url.host == "api.dexscreener.com":
            mint = request.url.path.rsplit("/", 1)[-1]
            self.calls.append(("dexscreener", mint))
            return httpx.Response(200, json=self.pairs.get(mint, []))
        body = json.loads(request.content)
        method, first = body["method"], body["params"][0]
        self.calls.append((method, first))
        if method == "getSignaturesForAddress":
            result = self.signatures.get(first, [])
        elif method == "getTransaction":
            result = self.txs.get(first)
        elif method == "getAccountInfo":
            info = self.mints.get(first)
            result = {"context": {"slot": 1}, "value": None if info is None else {
                "owner": TOKEN_PROGRAM_ID, "data": {"program": "spl-token", "parsed": {"type": "mint", "info": info}}}}
        else:
            return httpx.Response(400, json={"error": f"unexpected {method}"})
        return httpx.Response(200, json={"jsonrpc": "2.0", "id": 1, "result": result})


def run_chain() -> None:
    if not os.environ.get("DATABASE_URL"):
        print("SKIP chain: DATABASE_URL not set (needs a migrated disposable Postgres).")
        return

    from sqlmodel import select

    from ..db import async_session_factory
    from ..ingestion.solana import (
        POLLED_WALLETS,
        RAYDIUM_AMM_PROGRAM_ID,
        _poll_wallet,
        crawl_candidate_wallets,
        refresh_open_spl_positions,
    )
    from ..main import app
    from ..models import (
        BinanceCredential,
        IngestionError,
        PaperOrder,
        PaperTrade,
        Position,
        RiskCheck,
        SystemEvent,
        Token,
        TradingSignal,
        User,
        Wallet,
        WalletObservation,
    )
    from ..risk.engine import _dispatch_pending, _monitor_positions
    from .wallet_scorer import update_wallet_scores

    chain = FakeChain()
    good, weak = _address("SynthGood"), _address("SynthWeak")
    safe_mint, rug_mint = _address("SynthMint"), _address("SynthRug")
    mint_info = {"decimals": 6, "isInitialized": True, "supply": "1000000000", "mintAuthority": None}
    chain.mints[safe_mint] = {**mint_info, "freezeAuthority": None}
    chain.mints[rug_mint] = {**mint_info, "freezeAuthority": _address("SynthAuth")}  # can freeze holders
    for mint in (safe_mint, rug_mint):
        chain.pairs[mint] = [{"baseToken": {"address": mint, "symbol": "SYN"}, "priceUsd": "0.5",
                              "liquidity": {"usd": 500000.0}, "volume": {"h24": 5000000.0}}]

    # History, hours old (so stale): two round trips each. Good buys 100 tokens for 1 SOL and sells them
    # for 1.5 SOL; weak sells them for 0.5 SOL.
    now = int(time.time())
    for wallet, sell_lamports in ((good, 1_500_000_000), (weak, 500_000_000)):
        sigs = []
        for i in range(2):
            t = now - 3600 * (4 - 2 * i)
            buy, sell = f"synth-{wallet[:12]}-buy{i}", f"synth-{wallet[:12]}-sell{i}"
            chain.txs[buy] = _swap_tx(wallet, safe_mint, -1_000_000_000, "0", "100", t)
            chain.txs[sell] = _swap_tx(wallet, safe_mint, sell_lamports, "100", "0", t + 600)
            sigs += [{"signature": buy, "blockTime": t}, {"signature": sell, "blockTime": t + 600}]
        chain.signatures[wallet] = sorted(sigs, key=lambda s: -s["blockTime"])

    async def run():
        async with httpx.AsyncClient(transport=httpx.ASGITransport(app=app), base_url="http://test") as api, \
                httpx.AsyncClient(transport=httpx.MockTransport(chain.handler)) as rpc:
            r = await api.post("/api/v1/auth/register", json={"email": "chain-admin@test.local", "password": "pw-at-least-8"})
            assert r.status_code == 200 and r.json()["role"] == "admin", r.text

            # 1. Discovery intake by the operator.
            assert (await api.post("/api/v1/admin/wallets", json={"address": "not-base58-0OIl"})).status_code == 422
            for w in (good, weak):
                r = await api.post("/api/v1/admin/wallets", json={"address": w})
                assert r.status_code == 201 and r.json()["status"] == "DISCOVERED", r.text
            assert (await api.post("/api/v1/admin/wallets", json={"address": good})).status_code == 409
            # Approval before scoring is refused: the score gate can't be skipped.
            assert (await api.patch(f"/api/v1/admin/wallets/{good}", json={"status": "ACTIVE_MONITORED"})).status_code == 409

            async with async_session_factory() as s:
                admin = (await s.exec(select(User))).one()
                s.add(BinanceCredential(user_id=admin.id, api_key_encrypted="x", api_secret_encrypted="x"))
                await s.commit()

                # 2. Ingestion records the stale history for scoring, copies none of it, DLQs none of it.
                wallets = {w.address: w for w in (await s.exec(POLLED_WALLETS)).all()}
                assert set(wallets) == {good, weak}, set(wallets)
                for w in wallets.values():
                    await _poll_wallet(rpc, s, w)
                await _poll_wallet(rpc, s, wallets[good])  # a re-poll must not duplicate anything
                assert len((await s.exec(select(WalletObservation))).all()) == 8
                assert (await s.exec(select(IngestionError))).all() == []
                assert (await s.exec(select(TradingSignal))).all() == []
                assert not [c for c in chain.calls if c[0] in ("dexscreener", "getAccountInfo")], "history must not cost API calls"

                # 3. Scoring promotes only the strong wallet.
                await update_wallet_scores(s)
                assert wallets[good].status == "PENDING_REVIEW" and wallets[good].composite_score >= 70, wallets[good]
                assert wallets[weak].status == "DISCOVERED" and wallets[weak].composite_score < 70, wallets[weak]

            # 4. The operator approves the promoted wallet; the weak one can't be approved.
            r = await api.patch(f"/api/v1/admin/wallets/{good}", json={"status": "ACTIVE_MONITORED"})
            assert r.status_code == 200 and r.json()["status"] == "ACTIVE_MONITORED" and r.json()["approved_at"], r.text
            assert (await api.patch(f"/api/v1/admin/wallets/{weak}", json={"status": "ACTIVE_MONITORED"})).status_code == 409

            async with async_session_factory() as s:
                approved = (await s.exec(select(Wallet).where(Wallet.address == good))).one()
                assert (await s.exec(select(SystemEvent).where(SystemEvent.event_type == "WALLET_APPROVED"))).first()

                # 5. Fresh swaps of the approved wallet: the BUY of a safe token is mirrored; a SELL and a
                #    BUY of a token whose freeze authority is still set are not.
                fresh = int(time.time()) - 2
                live = {"synth-live-buy": _swap_tx(good, safe_mint, -2_000_000_000, "0", "300", fresh),
                        "synth-live-sell": _swap_tx(good, safe_mint, 1_500_000_000, "300", "100", fresh),
                        "synth-live-rug": _swap_tx(good, rug_mint, -1_000_000_000, "0", "50", fresh)}
                chain.txs.update(live)
                chain.signatures[good] = [{"signature": sig, "blockTime": fresh} for sig in live] + chain.signatures[good]
                await _poll_wallet(rpc, s, approved)

                signals = (await s.exec(select(TradingSignal))).all()
                assert len(signals) == 1, [(x.symbol, x.action) for x in signals]
                [signal] = signals
                assert signal.action == "BUY" and signal.status == "PENDING", signal
                assert signal.target_entry_price == Decimal("0.5"), signal.target_entry_price  # USD, from DEXScreener
                token = await s.get(Token, signal.token_id)
                assert token.address == safe_mint and token.mint_authority_revoked and token.freeze_authority_revoked
                assert token.pool_liquidity_usd == Decimal("500000.00"), token.pool_liquidity_usd
                rejected = [e.message for e in (await s.exec(
                    select(SystemEvent).where(SystemEvent.event_type == "COPY_TRADE_REJECTED"))).all()]
                assert any("SELL_NOT_MIRRORED" in m for m in rejected), rejected
                assert any("TOKEN_UNSAFE_AUTHORITY_NOT_REVOKED" in m for m in rejected), rejected

                # 6. The risk engine judges the mirrored signal under the DEX spread/fee model (F-16).
                #    A liquid DEX pool (liquidity $500k) has modeled spread 0.64% <= max_dex_spread_pct (2.5%),
                #    so it passes the Risk Gate and opens a paper order and position on the SPL token.
                await _dispatch_pending(s)
                [check] = (await s.exec(select(RiskCheck).where(RiskCheck.trading_signal_id == signal.id))).all()
                assert check.passed and check.rejection_reasons == [], check.rejection_reasons
                orders = (await s.exec(select(PaperOrder))).all()
                assert len(orders) == 1 and orders[0].status == "FILLED", orders
                positions = (await s.exec(select(Position).where(Position.token_id == token.id))).all()
                assert len(positions) == 1 and positions[0].status == "OPEN", positions
                trades = (await s.exec(select(PaperTrade).where(PaperTrade.position_id == positions[0].id))).all()
                assert len(trades) >= 1 and trades[0].execution_venue == "SOLANA_DEX_SIM", trades

                # 7. Continuous price poller updates open SPL position prices & triggers TP1 exit.
                # Increase price on DEXScreener to $0.55 (above tp1 $0.5375)
                chain.pairs[safe_mint][0]["priceUsd"] = "0.55"
                new_snaps = await refresh_open_spl_positions(rpc, s)
                assert len(new_snaps) >= 1 and new_snaps[0].price_usd == Decimal("0.55")

                await _monitor_positions(s)
                pos = (await s.exec(select(Position).where(Position.token_id == token.id))).one()
                assert pos.is_tp1_hit and pos.status == "PARTIALLY_CLOSED", pos.status
                assert pos.current_stop_loss == pos.average_entry_price

                # 8. Automated crawler discovers new candidate wallets from DEX activity (F-16).
                crawler_wallet = _address("SynthCrawl")
                chain.signatures[RAYDIUM_AMM_PROGRAM_ID] = [{"signature": "crawl-tx-1", "blockTime": fresh}]
                chain.txs["crawl-tx-1"] = {
                    "slot": 1,
                    "blockTime": fresh,
                    "meta": {"fee": 5000, "logMessages": []},
                    "transaction": {
                        "message": {
                            "accountKeys": [
                                {"pubkey": crawler_wallet, "signer": True},
                                {"pubkey": RAYDIUM_AMM_PROGRAM_ID, "signer": False},
                            ]
                        }
                    },
                }
                crawled = await crawl_candidate_wallets(rpc, s, limit=1)
                assert len(crawled) == 1 and crawled[0].address == crawler_wallet
                assert crawled[0].status == "DISCOVERED"
                assert (await s.exec(select(SystemEvent).where(SystemEvent.event_type == "WALLET_DISCOVERED"))).first()

            # 9. Admin crawler endpoint triggers discovery via HTTP API.
            import src.api.admin_routes as admin_routes_mod
            orig_client = admin_routes_mod.httpx.AsyncClient
            admin_routes_mod.httpx.AsyncClient = lambda *a, **kw: httpx.AsyncClient(transport=httpx.MockTransport(chain.handler))
            try:
                r_crawl = await api.post("/api/v1/admin/wallets/crawl?limit=5")
                assert r_crawl.status_code == 200 and "discovered_count" in r_crawl.json()
            finally:
                admin_routes_mod.httpx.AsyncClient = orig_client

            # 10. Archiving a wallet stops it being polled.
            assert (await api.patch(f"/api/v1/admin/wallets/{weak}", json={"status": "ARCHIVED"})).status_code == 200
            async with async_session_factory() as s:
                assert {w.address for w in (await s.exec(POLLED_WALLETS)).all()} == {good, crawler_wallet}

    asyncio.run(run())


if __name__ == "__main__":
    run_chain()
    print("ok")
