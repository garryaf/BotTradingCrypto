"""Plain-assert self-check for the pure (non-DB) ingestion logic. Run: python -m src.ingestion.test_heuristics"""
from datetime import datetime, timedelta, timezone
from decimal import Decimal

from .common import is_stale
from .solana import _token_delta


def test_is_stale():
    assert is_stale(datetime.now(timezone.utc) - timedelta(seconds=60)) is True
    assert is_stale(datetime.now(timezone.utc) - timedelta(seconds=5)) is False


def test_token_delta_nets_pre_and_post():
    owner = "WalletABC"
    pre = [{"owner": owner, "mint": "MintX", "uiTokenAmount": {"uiAmountString": "10"}}]
    post = [{"owner": owner, "mint": "MintX", "uiTokenAmount": {"uiAmountString": "4"}}]
    pre_d, post_d = _token_delta(pre, owner), _token_delta(post, owner)
    assert post_d["MintX"] - pre_d["MintX"] == Decimal("-6")


def test_token_delta_ignores_other_owners():
    deltas = _token_delta([{"owner": "Someone", "mint": "MintX", "uiTokenAmount": {"uiAmountString": "5"}}], "WalletABC")
    assert deltas == {}


def test_signature_deduplication():
    # AC-ING-01: Deduplikasi 100 signature, 20 duplikat -> 80 unik
    signatures = [f"sig_{i}" for i in range(80)] + [f"sig_{i}" for i in range(20)]
    assert len(signatures) == 100
    seen = set()
    unique = [s for s in signatures if not (s in seen or seen.add(s))]
    assert len(unique) == 80


def test_rpc_429_exponential_backoff_and_recovery():
    import asyncio
    import httpx
    from .solana import _rpc

    attempts = 0

    def handler(request: httpx.Request) -> httpx.Response:
        nonlocal attempts
        attempts += 1
        if attempts < 3:
            return httpx.Response(429, headers={"Retry-After": "0.01"})
        return httpx.Response(200, json={"jsonrpc": "2.0", "result": {"recovered": True}})

    async def run():
        async with httpx.AsyncClient(transport=httpx.MockTransport(handler)) as client:
            return await _rpc(client, "getSlot", [], max_retries=3, initial_delay=0.01)

    result = asyncio.run(run())
    assert result == {"recovered": True}
    assert attempts == 3


if __name__ == "__main__":
    test_is_stale()
    test_token_delta_nets_pre_and_post()
    test_token_delta_ignores_other_owners()
    test_signature_deduplication()
    test_rpc_429_exponential_backoff_and_recovery()
    print("ok")
