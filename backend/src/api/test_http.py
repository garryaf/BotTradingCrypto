"""HTTP-level self-check for the FastAPI app against a real Postgres.

Exercises the auth + dashboard + control routes end-to-end over ASGI (no network,
no background loops — lifespan is intentionally NOT run so the 6 ingestion/agent
loops stay off). Needs DATABASE_URL pointing at a migrated disposable DB and the
two startup secrets. Run:
    DATABASE_URL=... JWT_SECRET_KEY=x FIELD_ENCRYPTION_KEY=<fernet> \
        python -m src.api.test_http

Skips cleanly if DATABASE_URL isn't set, so it never breaks the pure self-checks.
"""
import asyncio
import os
import uuid
from decimal import Decimal

import httpx


def run_http() -> None:
    if not os.environ.get("DATABASE_URL"):
        print("SKIP http: DATABASE_URL not set (needs a migrated disposable Postgres).")
        return

    from ..main import app  # imported late: pulls in settings/db which need env

    async def run():
        transport = httpx.ASGITransport(app=app)  # ASGITransport does NOT run lifespan -> loops stay off
        # Use https base when the cookie is Secure (prod) so the client sends it back.
        scheme = "https" if os.environ.get("APP_ENV", "development") != "development" else "http"
        async with httpx.AsyncClient(transport=transport, base_url=f"{scheme}://test") as c:
            email = f"user-{uuid.uuid4().hex[:8]}@test.local"

            # GAP-14: health reports DB + loop states; lifespan isn't run under ASGITransport, so no loops.
            h = await c.get("/api/v1/health")
            assert h.status_code == 200, h.text
            assert h.json()["status"] == "ok" and h.json()["db"] == "connected" and h.json()["tasks"] == {}, h.json()

            # Unauthenticated routes are rejected.
            assert (await c.get("/api/v1/auth/me")).status_code == 401
            assert (await c.get("/api/v1/portfolio")).status_code == 401
            # Admin-only control rejects anonymous callers.
            assert (await c.post("/api/v1/control/kill")).status_code == 401
            # F-03: signals now requires auth (was unauthenticated + global).
            assert (await c.get("/api/v1/signals")).status_code == 401
            # F-09: wallets endpoint also requires auth.
            assert (await c.get("/api/v1/wallets")).status_code == 401
            assert (await c.get("/api/v1/admin/metrics")).status_code == 401

            # First registered user becomes admin (auth_routes.py).
            r = await c.post("/api/v1/auth/register", json={"email": email, "password": "pw-at-least-8"})
            assert r.status_code == 200, r.text
            assert r.json()["role"] == "admin", r.json()
            assert c.cookies.get("access_token"), "login cookie not set"
            # F-04: Secure flag follows env — present outside development, absent in dev (local HTTP).
            set_cookie = r.headers.get("set-cookie", "")
            if os.environ.get("APP_ENV", "development") == "development":
                assert "Secure" not in set_cookie, set_cookie
            else:
                assert "Secure" in set_cookie, set_cookie

            # Duplicate email -> 409 (use a valid-length password so it passes input validation first).
            assert (await c.post("/api/v1/auth/register", json={"email": email, "password": "pw-at-least-8"})).status_code == 409

            # F-05: input validation rejects bad email / short password with 422.
            assert (await c.post("/api/v1/auth/register", json={"email": "not-an-email", "password": "longenough"})).status_code == 422
            assert (await c.post("/api/v1/auth/register", json={"email": "ok@test.local", "password": "short"})).status_code == 422

            # Login is bounded, not policy-checked: a wrong short password is 401 (not 422), the right one 200.
            assert (await c.post("/api/v1/auth/login", json={"email": email, "password": "short"})).status_code == 401
            assert (await c.post("/api/v1/auth/login", json={"email": email, "password": "pw-at-least-8"})).status_code == 200
            # F-21: bcrypt>=5 raises past 72 bytes — both endpoints must answer 422, never 500.
            too_long = "a" * 73
            assert (await c.post("/api/v1/auth/register", json={"email": "long@test.local", "password": too_long})).status_code == 422
            assert (await c.post("/api/v1/auth/login", json={"email": email, "password": too_long})).status_code == 422

            me = await c.get("/api/v1/auth/me")
            assert me.status_code == 200 and me.json()["email"] == email

            # Portfolio seeds the initial paper capital for a fresh account.
            p = await c.get("/api/v1/portfolio")
            assert p.status_code == 200, p.text
            assert float(p.json()["equity_usd"]) > 0, p.json()

            # Positions empty for a new account.
            pos = await c.get("/api/v1/positions")
            assert pos.status_code == 200 and pos.json() == []

            # F-03: authenticated signals returns 200 (list); out-of-range backtest days is rejected 422
            # (query validation fires without running the outbound historical fetch).
            sig = await c.get("/api/v1/signals")
            assert sig.status_code == 200 and isinstance(sig.json(), list)
            # F-09: wallets endpoint (auth required, returns list).
            assert (await c.get("/api/v1/wallets")).status_code == 200
            w = await c.get("/api/v1/wallets")
            assert w.status_code == 200 and isinstance(w.json(), list)
            assert (await c.get("/api/v1/backtest/run", params={"days": 99999})).status_code == 422
            assert (await c.get("/api/v1/backtest/run", params={"days": 0})).status_code == 422

            # Dashboard labels get the enforced thresholds from the backend (single source).
            rs = await c.get("/api/v1/risk/status")
            assert rs.status_code == 200, rs.text
            assert rs.json()["limits"]["max_open_positions"] == 5 and rs.json()["limits"]["max_risk_per_trade_pct"] == 0.005

            # Binance credentials round-trip (Fernet encrypt/decrypt last4).
            put = await c.put("/api/v1/auth/binance-credentials", json={"api_key": "AKIexamplekey1234", "api_secret": "secretval9876"})
            assert put.status_code == 200 and put.json()["api_key_last4"] == "1234", put.text
            got = await c.get("/api/v1/auth/binance-credentials")
            assert got.json() == {"configured": True, "api_key_last4": "1234"}, got.json()

            # Admin can list users and run the kill switch (<2s path).
            users = await c.get("/api/v1/admin/users")
            assert users.status_code == 200 and len(users.json()) == 1
            kill = await c.post("/api/v1/control/kill")
            assert kill.status_code == 200 and kill.json()["engaged"] is True, kill.text
            assert kill.json()["elapsed_ms"] < 2000, kill.json()  # AC-CTL-01
            resume = await c.post("/api/v1/control/resume")
            assert resume.status_code == 200 and resume.json()["paused"] is False

            # GAP-14: admin metrics aggregate the last 24h of existing tables, incl. AI cost.
            from ..control.telegram_bot import _format_status
            from ..db import async_session_factory
            from ..models import AgentRun, LLMRequest
            from . import control as control_actions

            async with async_session_factory() as s:
                # F-25: Telegram /status must format what system_status() really returns.
                assert "Circuit Breaker" in _format_status(await control_actions.system_status(s))
                run_row = AgentRun(agent_name="TEST", task_type="METRICS", status="SUCCESS")
                s.add(run_row)
                await s.commit()
                s.add_all([
                    LLMRequest(agent_run_id=run_row.id, model_name="test", latency_ms=Decimal(100),
                               cost_usd=Decimal("0.0123"), prompt_tokens=100, completion_tokens=50),
                    LLMRequest(agent_run_id=run_row.id, model_name="test", latency_ms=Decimal(300), status_code=422),
                ])
                await s.commit()
            m = await c.get("/api/v1/admin/metrics")
            assert m.status_code == 200, m.text
            llm = m.json()["llm"]
            assert llm["requests"] >= 2 and llm["errors"] >= 1 and llm["tokens"] >= 150, llm
            assert float(llm["cost_usd"]) >= 0.0123, llm
            assert {"agent_runs", "signals", "risk_checks", "ingestion_errors", "critical_events"} <= m.json().keys()

    asyncio.run(run())


if __name__ == "__main__":
    run_http()
    print("ok")
