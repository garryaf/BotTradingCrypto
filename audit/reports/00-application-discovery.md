# 00 — Application Discovery

**Phase:** A (READ-ONLY). Every statement below is backed by a file read; unverified items are marked.

## 1. Actual application architecture
A single FastAPI process (`src/main.py`) that, on startup, (a) enforces a hard paper-trading lock and (b) spawns six long-running asyncio background loops, then serves a REST+health API. A separate Next.js dashboard polls the API over cookie-auth. An optional Rust microservice can be enabled to double-check risk verdicts. PostgreSQL 16 is the only datastore.

Data flow (verified in code):
```
Binance REST/WS ─┐
Solana RPC ──────┤→ ingestion loops → market_snapshots / market_ohlcv / wallet_observations
                 │                           │
                 │     solana.py swap on an APPROVED wallet → copy_trade.create_copy_trade_signal → trading_signals(PENDING)
                 │
Hermes loop (every 300s) → 3 LLM skill calls (regime→safety→signal) → trading_signals(PENDING)
                 │
Risk engine loop (every 5s): expire stale signals → for each PENDING × each account:
     evaluate_risk() [9 gates, Python]  AND  optional call_risk_engine() [Rust]
       → on pass: simulate_fills() → paper_orders + paper_trades + positions
       → monitor open positions (TP1 half-close→breakeven SL, TP2/SL full close) → portfolio_snapshots
                 │
Telegram loop + api/control.py → user_settings flags (pause/kill), system_events
```

**Safety-by-design is real and structural:** Hermes only ever writes `agent_runs`, `llm_requests`, `trading_signals` (PENDING). It has no code path to `paper_orders`/`positions`/`balances`. LLM output is constrained to Pydantic schemas (`agents/schemas.py`), and only the deterministic risk engine can open a position. Live execution is blocked three ways at startup (`assert_paper_mode()`, `live_trading_enabled is not False` RuntimeError, and there is simply no live-exchange order code).

## 2. AI agent workflow — reality vs the "4 agents" claim
The prompt/README expect 4 agents (Market Analyst, Coin Researcher, Risk Manager, Trading Executor). **The code does not implement four agent instances.** What exists:

| Expected role | Actual implementation | Type |
|---|---|---|
| Market Analyst | Hermes skill call #1 `market-regime-detection` → `RegimeResult` | LLM call |
| Coin Researcher | Hermes skill call #2 `token-and-contract-safety` → `SafetyResult`; indicators (EMA/RSI) computed in Python | LLM call + deterministic |
| (signal synthesis) | Hermes skill call #3 `signal-scoring-hybrid` → `SignalResult` (produces BUY/SELL + prices) | LLM call |
| Risk Manager | `risk/gate.py` + optional Rust engine — **deterministic, not an LLM agent** | code |
| Trading Executor | `risk/engine.py` + `broker.py` — **deterministic paper broker, not an LLM agent** | code |

So "agents" = one orchestrator (`HERMES`) making 3 sequential structured LLM calls, logged as a single `AgentRun(agent_name="HERMES", task_type="SIGNAL_SYNTHESIS")`, plus a second non-LLM signal source `COPY_TRADE`, plus two deterministic stages. This is a **sound and safer** design than 4 autonomous agents, but it does **not** match the documented 4-agent model. Finding F-01.

Skills (LLM prompts) live in `.agents/skills/*/SKILL.md`, loaded at runtime by `agents/skills.py` and mounted read-only into the container. Six skill dirs exist: market-regime-detection, token-and-contract-safety, signal-scoring-hybrid, risk-gate-validation, position-sizing-compounding, token-and-contract-safety. Only the first three are invoked by `hermes.py`; the rest appear to be reference/knowledge prompts for deterministic code (not confirmed wired).

## 3. Implemented features (verified by reading the code)
- ✅ Cookie-session auth (bcrypt + HS256 JWT, httpOnly cookie), first-registered-user becomes admin.
- ✅ Per-user encrypted Binance credentials (Fernet field encryption).
- ✅ Admin user management (list / change role / enable-disable), with self-demote guard.
- ✅ Deterministic 9-gate Risk Gate (pure function, unit-tested).
- ✅ Paper broker: slippage, partial fills, taker fees, TP1 half-close + breakeven SL, TP2/SL close; per-account portfolio snapshots with HWM/drawdown/daily-loss and auto circuit breaker.
- ✅ Hermes LLM pipeline with OpenRouter→9Route fallback and strict schema validation.
- ✅ Copy-trade signal generation from approved Solana wallets (wired via solana ingestion).
- ✅ Global + per-account kill/pause/resume; `/kill` cancels PENDING signals synchronously (<2s target).
- ✅ Telegram control bot (/status, /pause, /resume, /kill) with chat-id allowlist + operator push alerts.
- ✅ Optional Rust risk engine with fail-closed IPC client.
- ✅ Backtest engine reusing the same gate/broker (anti look-ahead by construction).
- ✅ Next.js dashboard: equity hero, positions table, signal log, risk-gate panel, candle chart (Binance WS), admin page, settings, login/register, hold-to-confirm kill switch.
- ✅ Alembic migrations 001→005 (linear chain), 21 SQLModel tables.

## 4. Documented but NOT found / NOT wired (verified)
- ❌ **Four distinct AI agents** — not implemented as such (F-01).
- ❌ **`wallet_scorer.update_wallet_scores` never invoked at runtime** — only called from its own test; no loop in main.py runs wallet scoring, so wallet composite scores are never computed in production, which means wallets never auto-promote DISCOVERED→PENDING_REVIEW and copy-trade's "APPROVED wallet" precondition can only ever be met by manual DB edits (F-07).
- ❌ **`/positions` Telegram command** — documented in README SOP, not implemented in telegram_bot.py (F-08).
- ❌ **Nginx config / UFW rules as repo artifacts** — only in README prose (F-11).
- ❓ **Wallet watchlist approval UI** — `frontend/wallets` renders a `WalletExplorer` placeholder (`NotConnected`), i.e. not implemented in the UI (F-09). RTM marks FR-WLT-03 ✅.
- ❓ OPEN_QUESTIONS.md and several 02/03/05 docs are cited by code but their existence was not confirmed this phase.

## 5. Exists but UNVERIFIED (needs Phase B+ test execution)
- All backend self-check tests (`test_*.py`) — present but not executed this phase (require the Docker container / deps). README claims they print "ok".
- Risk engine end-to-end (signal→order→position→snapshot) — logic read, never run.
- Rust engine `/evaluate` runtime behavior and Python↔Rust verdict consistency (static read shows **threshold divergence**, see F-02).
- Ingestion loops against live/mock Binance/Solana — not run.
- Backtest numeric correctness — not run.
- Frontend rendering / interactions — no test tooling exists; not run.
- Migrations applying cleanly on a fresh DB — not run.

## 6. Initial risks requiring immediate attention
- **F-02 (High):** Rust and Python gates use **different thresholds and a different expectancy formula**. Because verdicts are AND-ed, Rust is directionally fail-safe (can only make the system stricter), but a signal passing Python can be silently rejected by Rust for the wrong reason, and the two "9 gates" are not the same 9. If anyone ever relied on Rust alone, limits would be wrong (max positions <3 vs <5, risk/trade ≤2% vs ≤0.5%, spread ≤5% vs ≤0.08%, expectancy ignores fees). Safety-critical to reconcile before any live phase.
- **F-03 (Medium/High):** `GET /api/v1/signals` is **unauthenticated and global** — leaks every account's signals + rationale. `GET /api/v1/backtest/run` is unauthenticated with an unbounded `days` param (outbound-fetch abuse).
- **F-07 (High for the copy-trade feature):** wallet scoring never runs → copy-trade effectively inert in a clean deployment.
- **F-04 (Medium):** session cookie not marked `secure`; Telegram allowlist checks chat_id only (not sender user id) — any member of the allowed chat can `/kill`.
- **Positive safety confirmations:** no LLM→order direct path; live trading triple-locked; secrets not logged; fail-closed engine client; `/kill` synchronous.
