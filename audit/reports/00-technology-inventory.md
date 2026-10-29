# 00 — Technology & Dependency Inventory

**Phase:** A (Discovery, READ-ONLY). Versions are from manifests, not resolved lockfiles unless noted.

## Backend (`backend/pyproject.toml`)
Package `autotrade-backend` 0.1.0, `requires-python >=3.12`.

| Dependency | Declared | Expected (prompt) | Match |
|---|---|---|---|
| fastapi | >=0.115 | FastAPI | ✓ |
| uvicorn[standard] | >=0.32 | — | ✓ |
| sqlmodel | >=0.0.22 | SQLModel | ✓ |
| asyncpg | >=0.30 | AsyncPG | ✓ |
| greenlet | >=3.1 | — | (SQLAlchemy async dep) |
| httpx | >=0.27 | — | used for gateway/engine/telegram/ingestion |
| alembic | >=1.14 | Alembic | ✓ |
| pydantic-settings | >=2.6 | Pydantic v2 | ✓ (implies pydantic v2) |
| bcrypt | >=4.2 | — | password hashing |
| pyjwt | >=2.9 | — | JWT sessions |
| cryptography | >=43.0 | — | Fernet field encryption |

No test/lint dev-dependency group declared. Tests are plain-`assert` self-checks run as `python -m src.<pkg>.test_*` (confirmed in `test_gate.py`). **No pytest, ruff, mypy, or coverage tooling declared.**

## Rust engine (`engine/Cargo.toml` + `src/main.rs`)
Hand-rolled HTTP server on `std::net::TcpListener` (no framework). Deps: `serde`, `serde_json` (inferred from imports; Cargo.toml not fully read this phase). Has `#[cfg(test)]` unit tests (4) run via `cargo test`.

## Frontend (`frontend/package.json`) — via sub-agent
Next.js **15.5.28**, React **19.1.0**, react-dom 19.1.0, Tailwind **v4**, framer-motion **^14.4.0**, lightweight-charts **^5.2.1**, lucide-react **^1.60.0**, TypeScript ^5, eslint ^9 / eslint-config-next 15.5.28. Scripts: dev/build/start/lint. **No test runner (no Playwright/Jest/Vitest/Testing Library).**

> ⚠️ `framer-motion ^14.4.0` and `lucide-react ^1.60.0` are unusually high major versions vs their known public release lines. Not verified against the registry this phase — recommend confirming they resolve to real published releases (supply-chain / typo check) in the dependency audit. See discovery report risk R-05.

## Infrastructure
- **PostgreSQL 16-alpine** (both compose files). ✓ matches expected stack.
- **Docker / Docker Compose** — `docker-compose.yml` (dev, bind-mounts source, publishes 5432/8000/3000 to all interfaces) and `docker-compose.prod.yml` (binds ports to `127.0.0.1`, named volume, healthcheck, `restart: always`, isolated `internal_net`).
- **Rust engine** service gated behind compose `profiles: ["engine"]` + `ENGINE_URL`.
- **Nginx / UFW / Certbot** — documented in README as manual host setup; **no nginx config or UFW rules file in the repo** (config lives only in README prose). Flagged F-11.
- Backend Dockerfile: `python:3.12-slim`, `pip install -e .`, CMD runs `alembic upgrade head && uvicorn`.
- Frontend Dockerfile: multi-stage node:20-alpine, non-root `nextjs` user, `npm run start`. Note: not using Next `output: standalone` (next.config.ts is empty), so the runner copies full `node_modules`.

## External integrations observed in code
OpenRouter + 9Route (gateway), Binance public market-data domains `data-api.binance.vision` / `data-stream.binance.vision` (frontend charts) and Binance ingestion (backend), Solana RPC (Helius or public fallback), Telegram Bot API, optional Rust engine `/evaluate`.

## Version/config discrepancies (confirmed)
- `config.py` default `openrouter_default_model = "anthropic/claude-haiku-5.5"`; `.env.example` says `anthropic/claude-3.5-haiku`; README prod example says `claude-3.5-sonnet`. Three different defaults. (Model string "claude-haiku-5.5" is not a known released model id — verify.)
- `requires-python >=3.12` but host interpreter is 3.14. Containerized runtime is 3.12-slim, so runtime is fine; local non-Docker runs may drift.
