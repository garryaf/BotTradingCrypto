"""Telegram control bot — ROADMAP.md TASK-5.4. Long-polling via raw HTTP
(httpx is already a dependency; no need for python-telegram-bot for 4
commands). Unregistered chat IDs are ignored without any reply, per
docs/05-security/RBAC_AND_TELEGRAM_ACCESS.md.
"""
import asyncio
import logging

import httpx

from ..api import control as control_actions
from ..config import settings
from ..db import async_session_factory

logger = logging.getLogger("control.telegram")

API_BASE = "https://api.telegram.org"
POLL_TIMEOUT_SEC = 25


def _is_configured() -> bool:
    return bool(settings.telegram_bot_token) and "1234567890" not in settings.telegram_bot_token


def _is_allowed(chat_id: str, from_id: str) -> bool:
    """F-04: chat must be the allowlisted chat, and (if set) the sender must be the
    allowlisted user — otherwise any member of the chat could issue /kill."""
    if not chat_id or chat_id != settings.telegram_allowed_chat_id:
        return False
    if settings.telegram_allowed_user_id and from_id != settings.telegram_allowed_user_id:
        return False
    return True


async def _send_message(client: httpx.AsyncClient, chat_id: str, text: str) -> None:
    res = await client.post(f"{API_BASE}/bot{settings.telegram_bot_token}/sendMessage", json={"chat_id": chat_id, "text": text})
    res.raise_for_status()


async def notify_operator(text: str, client: httpx.AsyncClient | None = None) -> bool:
    """Sends a critical push alert to settings.telegram_allowed_chat_id (FR-TG-01, AC-CTL-03).
    Fails safely and never raises into the caller loop."""
    if not _is_configured() or not settings.telegram_allowed_chat_id:
        return False
    owns_client = client is None
    c = client or httpx.AsyncClient(timeout=5.0)
    try:
        await _send_message(c, settings.telegram_allowed_chat_id, text)
        return True
    except Exception as exc:
        logger.warning("Failed to send Telegram alert: %s", exc)
        return False
    finally:
        if owns_client:
            await c.aclose()


def _format_status(s: dict) -> str:
    """Formats control.system_status(): operator-wide fields only. Per-account money figures live on
    the dashboard — reading them here raised KeyError, so /status silently never replied (F-25)."""
    state = "🔴 PAUSED" if s["paused"] else "🟢 RUNNING"
    cb = "🚨 ACTIVE" if s["circuit_breaker_active"] else "off"
    return f"{state}\nPosisi terbuka (semua akun): {s['open_positions_count']}\nCircuit Breaker: {cb}"


def _format_positions(rows: list[dict]) -> str:
    if not rows:
        return "📭 Tidak ada posisi terbuka."
    lines = ["📊 Posisi Terbuka:"]
    for p in rows:
        lines.append(
            f"{p['symbol']}: {float(p['quantity']):.6f} @ ${float(p['average_entry_price']):.2f} "
            f"| PnL ${float(p['unrealized_pnl_usd']):.2f}"
        )
    return "\n".join(lines)


async def _handle_command(client: httpx.AsyncClient, chat_id: str, text: str) -> None:
    command = text.strip().split()[0].lower()
    async with async_session_factory() as session:
        if command == "/status":
            reply = _format_status(await control_actions.system_status(session))
        elif command == "/positions":
            reply = _format_positions(await control_actions.open_positions_detail(session))
        elif command == "/pause":
            await control_actions.pause_trading(session)
            reply = "⏸ Entry baru dihentikan sementara."
        elif command == "/resume":
            await control_actions.resume_trading(session)
            reply = "▶️ Sistem diaktifkan kembali (circuit breaker direset manual)."
        elif command == "/kill":
            result = await control_actions.emergency_stop(session)
            reply = f"🛑 EMERGENCY STOP — {result['cancelled_signals']} sinyal dibatalkan dalam {result['elapsed_ms']}ms."
        else:
            return
    await _send_message(client, chat_id, reply)


async def run_telegram_bot() -> None:
    if not _is_configured():
        logger.warning("Telegram bot idle: TELEGRAM_BOT_TOKEN not configured")
        return

    offset = 0
    async with httpx.AsyncClient(timeout=POLL_TIMEOUT_SEC + 10) as client:
        while True:
            try:
                res = await client.get(
                    f"{API_BASE}/bot{settings.telegram_bot_token}/getUpdates",
                    params={"offset": offset, "timeout": POLL_TIMEOUT_SEC},
                )
                res.raise_for_status()
                updates = res.json().get("result", [])
            except httpx.HTTPError as exc:
                logger.warning("Telegram getUpdates failed: %s", exc)
                await asyncio.sleep(5)
                continue

            for update in updates:
                offset = update["update_id"] + 1
                message = update.get("message") or {}
                chat_id = str(message.get("chat", {}).get("id", ""))
                from_id = str(message.get("from", {}).get("id", ""))
                text = message.get("text", "")
                if not text.startswith("/"):
                    continue
                if not _is_allowed(chat_id, from_id):
                    continue  # unregistered chat or sender — ignored without reply, per RBAC doc
                try:
                    await _handle_command(client, chat_id, text)
                except Exception:
                    logger.exception("Telegram command handling failed")
