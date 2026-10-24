"""Plain-assert self-check for Telegram bot push alerts & commands (FR-TG-01, AC-CTL-02, AC-CTL-03).
Run: python -m src.control.test_telegram_bot
"""
import asyncio
import httpx

from .. import config
from .telegram_bot import notify_operator


def test_notify_operator_when_unconfigured():
    config.settings.telegram_bot_token = ""
    config.settings.telegram_allowed_chat_id = ""
    res = asyncio.run(notify_operator("Test alert"))
    assert res is False


def test_notify_operator_success_with_mock_client():
    config.settings.telegram_bot_token = "999999999:AAFakeTokenForTest"
    config.settings.telegram_allowed_chat_id = "12345678"

    recorded_payloads = []

    def handler(request: httpx.Request) -> httpx.Response:
        import json
        recorded_payloads.append(json.loads(request.content))
        return httpx.Response(200, json={"ok": True})

    client = httpx.AsyncClient(transport=httpx.MockTransport(handler))
    res = asyncio.run(notify_operator("🚨 Circuit Breaker Alert", client=client))
    assert res is True
    assert len(recorded_payloads) == 1
    assert recorded_payloads[0]["chat_id"] == "12345678"
    assert "Circuit Breaker Alert" in recorded_payloads[0]["text"]


def test_notify_operator_swallows_network_errors():
    config.settings.telegram_bot_token = "999999999:AAFakeTokenForTest"
    config.settings.telegram_allowed_chat_id = "12345678"

    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(500, json={"error": "telegram outage"})

    client = httpx.AsyncClient(transport=httpx.MockTransport(handler))
    res = asyncio.run(notify_operator("Alert", client=client))
    assert res is False  # Never raises into caller


if __name__ == "__main__":
    test_notify_operator_when_unconfigured()
    test_notify_operator_success_with_mock_client()
    test_notify_operator_swallows_network_errors()
    print("ok")
