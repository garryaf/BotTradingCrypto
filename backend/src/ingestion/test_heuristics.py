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


if __name__ == "__main__":
    test_is_stale()
    test_token_delta_nets_pre_and_post()
    test_token_delta_ignores_other_owners()
    print("ok")
