"""Plain-assert self-check for the fail-closed Rust engine client (RUST_ENGINE_INTEGRATION_SPEC.md §5).
No engine or DB needed. Run: python -m src.risk.test_engine_client
"""
import asyncio

import httpx

from .. import config
from .engine_client import call_risk_engine

CANDIDATE = {"signal_id": "sig-1", "symbol": "SOLUSDT", "action": "BUY"}
ALL_GATES = {"expectancy_check": True, "daily_loss_check": True, "data_freshness_check": True}


def _verdict(handler) -> tuple[bool, list[str]]:
    config.settings.engine_url = "http://engine.test:8080"

    async def run():
        async with httpx.AsyncClient(transport=httpx.MockTransport(handler)) as client:
            return await call_risk_engine(CANDIDATE, client)

    return asyncio.run(run())


def _json(body, status=200):
    return lambda request: httpx.Response(status, json=body)


def _raise(exc):
    def handler(request):
        raise exc("mocked", request=request)
    return handler


def test_engine_pass():
    assert _verdict(_json({"signal_id": "sig-1", "passed": True, "gates": ALL_GATES})) == (True, [])


def test_engine_rejection_reasons_are_kept():
    body = {"signal_id": "sig-1", "passed": False, "gates": {**ALL_GATES, "daily_loss_check": False},
            "rejection_reasons": ["DAILY_LOSS_EXCEEDED"]}
    assert _verdict(_json(body)) == (False, ["DAILY_LOSS_EXCEEDED"])


def test_timeout_fails_closed():
    assert _verdict(_raise(httpx.ReadTimeout)) == (False, ["ENGINE_TIMEOUT"])


def test_unreachable_engine_fails_closed():
    assert _verdict(_raise(httpx.ConnectError)) == (False, ["ENGINE_UNAVAILABLE"])


def test_5xx_fails_closed():
    assert _verdict(_json({"error": "boom"}, status=500)) == (False, ["ENGINE_ERROR"])


def test_non_json_fails_closed():
    assert _verdict(lambda request: httpx.Response(200, text="<html>oops</html>")) == (False, ["ENGINE_INVALID_RESPONSE"])


def test_schema_violation_fails_closed():
    assert _verdict(_json({"signal_id": "sig-1", "passed": "yes please"})) == (False, ["ENGINE_INVALID_RESPONSE"])


def test_passed_with_failed_gate_is_not_trusted():
    body = {"signal_id": "sig-1", "passed": True, "gates": {**ALL_GATES, "drawdown_check": False}}
    assert _verdict(_json(body)) == (False, ["ENGINE_INVALID_RESPONSE"])


def test_passed_with_no_gates_is_not_trusted():
    assert _verdict(_json({"signal_id": "sig-1", "passed": True, "gates": {}})) == (False, ["ENGINE_INVALID_RESPONSE"])


def test_verdict_for_another_signal_is_not_trusted():
    body = {"signal_id": "sig-OTHER", "passed": True, "gates": ALL_GATES}
    assert _verdict(_json(body)) == (False, ["ENGINE_INVALID_RESPONSE"])


if __name__ == "__main__":
    for name, fn in list(globals().items()):
        if name.startswith("test_"):
            fn()
    print("ok")
