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


async def _send_message(client: httpx.AsyncClient, chat_id: str, text: str) -> None:
    await client.post(f"{API_BASE}/bot{settings.telegram_bot_token}/sendMessage", json={"chat_id": chat_id, "text": text})


def _format_status(s: dict) -> str:
    state = "🔴 PAUSED" if s["paused"] else "🟢 RUNNING"
    cb = "🚨 ACTIVE" if s["circuit_breaker_active"] else "off"
    return (
        f"{state}\n"
        f"Equity: ${s['equity_usd']:.2f}\n"
        f"Cash: ${s['cash_balance_usd']:.2f} | Posisi: ${s['open_positions_value_usd']:.2f} ({s['open_positions_count']})\n"
        f"Daily PnL: ${s['daily_realized_pnl_usd']:.2f} ({s['daily_loss_pct']:.2f}% loss)\n"
        f"Drawdown: {s['current_drawdown_pct']:.2f}% | HWM: ${s['high_water_mark_usd']:.2f}\n"
        f"Circuit Breaker: {cb}"
    )


async def _handle_command(client: httpx.AsyncClient, chat_id: str, text: str) -> None:
    command = text.strip().split()[0].lower()
    async with async_session_factory() as session:
        if command == "/status":
            reply = _format_status(await control_actions.system_status(session))
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
                text = message.get("text", "")
                if not text.startswith("/"):
                    continue
                if not chat_id or chat_id != settings.telegram_allowed_chat_id:
                    continue  # unregistered chat — ignored without reply, per RBAC doc
                try:
                    await _handle_command(client, chat_id, text)
                except Exception:
                    logger.exception("Telegram command handling failed")
