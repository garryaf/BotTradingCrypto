"""AI Model Gateway — OpenRouter primer, 9Route fallback (Q-12, ROADMAP TASK-3.1/3.2).

Both providers are assumed OpenAI-compatible /chat/completions endpoints, per
Q-12's "ganti model tanpa mengubah kode adapter". A provider is skipped when
its API key is blank or still the .env.example placeholder.
"""
import time

import httpx

from ..config import settings

TIMEOUT_SEC = 15
MAX_TOKENS = 2500  # reasoning tokens count against this; 1000 truncated the JSON mid-object


class GatewayError(RuntimeError):
    pass


def _is_configured(api_key: str) -> bool:
    return bool(api_key) and "your_" not in api_key and "_here" not in api_key


def _providers() -> list[tuple[str, str, str, str]]:
    return [
        ("OPENROUTER", settings.openrouter_base_url, settings.openrouter_api_key, settings.openrouter_default_model),
        ("9ROUTE", settings.nineroute_base_url, settings.nineroute_api_key, settings.nineroute_default_model),
    ]


async def _call_one(
    client: httpx.AsyncClient, base_url: str, api_key: str, model: str, system_prompt: str, user_prompt: str
) -> tuple[str, dict]:
    res = await client.post(
        f"{base_url.rstrip('/')}/chat/completions",
        headers={"Authorization": f"Bearer {api_key}"},
        json={
            "model": model,
            "max_tokens": MAX_TOKENS,
            "response_format": {"type": "json_object"},
            "messages": [
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt},
            ],
        },
        timeout=TIMEOUT_SEC,
    )
    res.raise_for_status()
    body = res.json()
    return body["choices"][0]["message"]["content"], body.get("usage", {})


async def chat_completion_with_fallback(
    system_prompt: str, user_prompt: str, client: httpx.AsyncClient | None = None
) -> tuple[str, str, str, dict, float]:
    """Returns (provider, model, content, usage, latency_ms). Tries OpenRouter then 9Route."""
    owns_client = client is None
    client = client or httpx.AsyncClient()
    errors = []
    try:
        for name, base_url, api_key, model in _providers():
            if not base_url or not _is_configured(api_key):
                errors.append(f"{name}: not configured")
                continue
            start = time.monotonic()
            try:
                content, usage = await _call_one(client, base_url, api_key, model, system_prompt, user_prompt)
                return name, model, content, usage, round((time.monotonic() - start) * 1000, 2)
            except (httpx.HTTPError, KeyError, ValueError) as exc:
                errors.append(f"{name}: {exc}")
                continue
        raise GatewayError(f"all providers failed: {'; '.join(errors)}")
    finally:
        if owns_client:
            await client.aclose()
