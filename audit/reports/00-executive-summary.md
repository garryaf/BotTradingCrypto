# Executive Summary — Discovery Baseline (Phase A)

**Project:** BotTradingCrypto (formerly AUTO-TRADE-AA) — personal AI crypto trading + copy-trading platform
**Phase:** A — Discovery only. READ-ONLY. No application source, schema, config, or docs were modified.
**Date:** 2026-10-26
**Reported progress (owner estimate):** ~70%. **Independently verified this phase:** architecture and feature *presence* confirmed by code reading; **functional correctness NOT yet verified** (no tests executed).

## Method
Direct reads of manifests, entry points, risk/agent/auth/control code, models, migrations, Docker/compose, Rust engine, and frontend data layer, plus two `context-gatherer` sub-agents (frontend inventory; backend API/auth/telegram inventory). Toolchain checked read-only (docker/cargo/node present; backend deps run inside the container, not on host).

## What is implemented (presence confirmed by code)
Cookie-session auth with bcrypt+JWT and first-user-admin; Fernet-encrypted per-user Binance keys; admin user management; a deterministic 9-gate Python Risk Gate (unit-tested); a paper broker with slippage/partial-fill/fees/TP1-TP2-SL and per-account portfolio snapshots + auto circuit breaker; a Hermes LLM pipeline (3 structured skill calls, OpenRouter→9Route fallback, strict Pydantic output); copy-trade signal generation from approved Solana wallets; global + per-account kill/pause/resume with a <2s synchronous `/kill`; a chat-id-allowlisted Telegram control bot; an optional fail-closed Rust risk engine; a backtest engine reusing the live gate/broker; and a Next.js dashboard (equity, positions, signals, risk panel, live candle chart, admin, settings, hold-to-confirm kill switch). Migrations 001→005 form a clean linear chain over 21 tables.

## Verified features
See `00-application-discovery.md §3` — 14 feature areas present in code. Strongest, safety-relevant confirmations:
- **No LLM→order path.** LLM output is schema-bound and can only create a PENDING signal; only the deterministic engine opens positions.
- **Live trading triple-locked** at startup (`assert_paper_mode`, hard `live_trading_enabled` check, and no live-exchange order code at all).
- **Fail-closed engine client** and **synchronous emergency stop**.
- **Secrets not logged**; Binance keys only ever surfaced as last-4.

## Partially implemented / differs from docs
- **AI "4 agents" (F-01):** actually 1 orchestrator doing 3 LLM calls + 2 deterministic stages + a copy-trade source. Safer than documented, but not the documented shape.
- **Fail-closed by default (F-06):** the external Rust gate is off by default, so fail-closed protection is inactive unless `ENGINE_URL` is set (by design, but worth an explicit decision for live).

## Documented but NOT found / NOT wired
- **Wallet scoring (F-07, High for the feature):** `update_wallet_scores` is never called at runtime → wallets never auto-promote → copy-trade is inert in a clean deployment. RTM still marks it Fulfilled.
- **`/positions` Telegram command (F-08)** — documented, not implemented.
- **Wallet explorer UI (F-09)** — placeholder only.
- **Nginx/UFW (F-11)** — exist only as README prose, not repo artifacts.

## Confirmed findings by severity (12 total — all discovery-stage, confidence Confirmed)
- **Critical:** 0.
- **High:** 2 — F-02 (Python/Rust gate threshold+formula divergence), F-07 (wallet scoring unwired).
- **Medium:** 3 — F-03 (unauth `/signals` global leak + unauth unbounded `/backtest/run`), F-04 (cookie not Secure; Telegram allowlist chat-id only), F-10 (RTM overstates completion).
- **Low:** 4 — F-05 (no register/login input validation), F-08, F-09, F-11.
- **Informational:** 3 — F-01, F-06, F-12 (stale AUTO-TRADE-AA naming + broken README links).

## Findings requiring immediate safety attention
1. **F-02** — reconcile the Rust gate to the Python gate's thresholds and fee-aware expectancy before any live/staging phase. Today it is directionally safe only because verdicts are AND-ed.
2. **F-03** — add auth + user-scoping to `/signals`; add auth + bound `days` on `/backtest/run`.
3. **F-07** — wire or schedule wallet scoring (or document the manual approval path) so copy-trade isn't silently dead.

No condition was found that allows unintended **live** trading, bypass of the deterministic risk gate, or exposure of trading credentials. The data leak in F-03 is read-only metadata (signals), not credentials or funds.

## Untested / blocked areas (carry into later phases)
All runtime behavior is unverified: backend self-check tests, risk-engine end-to-end, Rust `/evaluate`, ingestion loops, backtest math, migration apply-on-fresh-DB, and the entire frontend (no test tooling exists). Running them needs the Docker stack (Postgres + backend deps) and, for the engine, `cargo test`. No external API keys are required for the self-check suite per README.

## Critical dependencies for deeper testing
Docker + Docker Compose, a disposable Postgres 16 test DB, the backend image build (installs deps), and `cargo` for the Rust tests. No production credentials; use testnet/mocks only (Rule 4).

## Production blockers (preliminary)
F-02 (gate parity), F-07 (dead copy-trade path), F-03/F-04 (auth hardening) should clear before staging. Nginx/UFW as code (F-11) and naming/doc honesty (F-10/F-12) before a clean reproducible deploy. A 30-day paper soak (Fase 6) is still in progress per README and is a stated gate for Fase 7.

## Recommended next audit domain
**Phase B2/B3 + Risk Gate tests**, executed inside Docker: build the backend image, run the plain-assert self-checks (`python -m src.risk.test_gate` etc.) and `cargo test`, then stand up a disposable Postgres to exercise the risk-engine end-to-end on synthetic signals. This directly retests F-02, F-06, F-07 and converts the many NOT_TESTED rows in `03-api-inventory.csv` / `04-agent-workflow-matrix.csv` into verified results.

---
*Discovery complete. Per the charter, stopping here for review before any deeper test execution, remediation, dependency install, live exchange call, or destructive DB operation.*
