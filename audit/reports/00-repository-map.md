# 00 — Repository Map

**Audit phase:** A (Discovery, READ-ONLY)
**Date:** 2026-10-26
**Repo:** BotTradingCrypto (formerly AUTO-TRADE-AA) — `autotrade-backend` v0.1.0
**Method:** Direct file reads + two `context-gatherer` sub-agents (frontend; backend API/auth/control/telegram). No source files modified.

> Note: the on-disk project directory is `BotTradingCrypto`, but code, env vars, DB names, and docs still carry the original `AUTO-TRADE-AA` / `autotrade` naming. README deep-links point at a stale `/SourceCode/AUTO-TRADE-AA/...` path. Cosmetic, not a defect; flagged in discovery report.

## Top-level layout

```
BotTradingCrypto/
├── backend/           # Python 3.12 FastAPI monolith (API + all background loops)
│   ├── src/
│   │   ├── agents/    # Hermes orchestrator, skills loader, schemas, indicators, wallet_scorer, copy_trade
│   │   ├── api/       # routes.py, auth_routes.py, admin_routes.py, control.py (service, not a router)
│   │   ├── auth/      # security.py (bcrypt/JWT/Fernet), dependencies.py (get_current_user/admin)
│   │   ├── backtest/  # engine.py, strategy.py, data.py
│   │   ├── control/   # telegram_bot.py (raw httpx long-poll)
│   │   ├── gateway/   # client.py (OpenRouter + 9Route fallback)
│   │   ├── ingestion/ # binance.py, solana.py, aggregator.py, common.py
│   │   ├── risk/      # gate.py (9 gates), engine.py (loop), broker.py, ledger.py, sizing.py, engine_client.py, burner_guard.py
│   │   ├── config.py  # Pydantic Settings
│   │   ├── db.py      # async engine + session factory
│   │   ├── models.py  # 21 SQLModel tables
│   │   └── main.py    # FastAPI app + lifespan task launcher
│   ├── alembic/versions/  # 001..005 (linear chain)
│   ├── Dockerfile
│   └── pyproject.toml
├── engine/            # Rust Risk Gate microservice (src/main.rs, Cargo.toml, Dockerfile) — opt-in
├── frontend/          # Next.js 15 App Router (React 19, Tailwind v4)
│   └── src/{app,components,lib,middleware.ts}
├── scripts/           # ram_soak_monitor.py, drill_db_restore.sh
├── docs/              # 15-domain documentation set + docs/audit/
├── .agents/           # ponytail rule + 6 skill prompt files (mounted RO into backend container)
├── .kiro/steering/    # ponytail.md (inclusion: always)
├── docker-compose.yml / docker-compose.prod.yml
└── .env.example
```

## Module boundaries (actual, verified)

| Layer | Modules | Writes to | Notes |
|---|---|---|---|
| Ingestion | `ingestion/binance.py`, `solana.py`, `aggregator.py` | market_snapshots, market_ohlcv, wallet_observations, ingestion_errors; **solana.py also triggers copy_trade** | 3 background loops |
| AI / signals | `agents/hermes.py`, `gateway/client.py`, `agents/copy_trade.py` | agent_runs, llm_requests, trading_signals (PENDING) | Hermes isolated from execution by design |
| Risk + execution | `risk/engine.py`, `gate.py`, `broker.py`, `ledger.py`, `engine_client.py` | risk_checks, paper_orders, paper_trades, positions, portfolio_snapshots | Only path that opens positions |
| Control | `api/control.py` (service), `control/telegram_bot.py` | user_settings (flags), system_events | Global + per-account kill/pause |
| API | `api/routes.py`, `auth_routes.py`, `admin_routes.py` | users, binance_credentials | 3 routers + inline `/health` |
| Frontend | `frontend/src/**` | — (read-only polling + public Binance WS) | Only mutating UI: auth, credentials, admin, kill/resume |

## Background tasks launched at startup (`main.py` lifespan)
`run_binance_ingestion`, `run_solana_ingestion`, `run_aggregator`, `run_hermes_loop`, `run_risk_engine_loop`, `run_telegram_bot`.
**Not launched:** `wallet_scorer.update_wallet_scores` (orphaned — see discovery report F-07).

## Toolchain present on host (read-only check)
python3 = 3.14.6 (project targets 3.12), cargo ✓, docker ✓, node ✓, npm ✓. No backend venv; `fastapi` not importable on host — backend tests are designed to run inside the Docker container (per README Step 5).
