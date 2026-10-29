"""Plain-assert self-check for Telegram bot push alerts & commands (FR-TG-01, AC-CTL-02, AC-CTL-03).
Run: python -m src.control.test_telegram_bot
"""
import asyncio
import httpx

from .. import config
from .telegram_bot import _format_status, _is_allowed, notify_operator


def test_status_formats_the_operator_summary():
    # Exactly the keys control.system_status() returns (test_http checks it against the real function).
    text = _format_status({"open_positions_count": 2, "paused": False, "circuit_breaker_active": True})
    assert "RUNNING" in text and "2" in text and "ACTIVE" in text


def test_allowlist_requires_matching_chat_and_sender():
    config.settings.telegram_allowed_chat_id = "100"
    config.settings.telegram_allowed_user_id = "200"
    assert _is_allowed("100", "200") is True
    assert _is_allowed("999", "200") is False  # wrong chat
    assert _is_allowed("100", "201") is False  # right chat, wrong sender (F-04)
    assert _is_allowed("", "200") is False


def test_allowlist_sender_optional_when_user_id_unset():
    config.settings.telegram_allowed_chat_id = "100"
    config.settings.telegram_allowed_user_id = ""  # not configured -> chat check only
    assert _is_allowed("100", "anything") is True
    assert _is_allowed("100", "") is True


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
    test_status_formats_the_operator_summary()
    test_allowlist_requires_matching_chat_and_sender()
    test_allowlist_sender_optional_when_user_id_unset()
    test_notify_operator_when_unconfigured()
    test_notify_operator_success_with_mock_client()
    test_notify_operator_swallows_network_errors()
    print("ok")
