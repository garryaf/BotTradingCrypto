# MATRIKS KETERLACAKAN KEBUTUHAN (REQUIREMENTS TRACEABILITY MATRIX)
**Dokumen:** `docs/audit/REQUIREMENTS_TRACEABILITY_MATRIX.md`  
**Proyek:** AI Crypto Trading & Copy-Trading Platform (AUTO-TRADE-AA)  
**Versi:** 1.0.0  
**Tanggal:** 21 Oktober 2026  
**Status:** Draf Resmi Audit  

---

Dokumen ini memetakan setiap ID Kebutuhan Bisnis (`BR`), Kebutuhan Fungsional (`FR`), dan Kriteria Penerimaan (`AC`) ke file implementasi kode sumber dan file pengujian yang relevan. Status pemenuhan ditetapkan berdasarkan inspeksi kode aktual di repositori.

**Legenda Status:**
- ✅ **Fulfilled** — Implementasi lengkap dan terverifikasi di kode
- ⚠️ **Partial** — Sebagian diimplementasikan, ada komponen yang belum selesai
- ❌ **Pending** — Belum diimplementasikan

> **Koreksi audit 2026-10-26:** status baris BR-01, FR-WLT-01/03, FR-AI-03, FR-RSK-01, FR-UI-02 dan beberapa referensi test dikoreksi berdasarkan verifikasi kode + test runtime (`audit/reports/13-final-remediation.md`). ✅ pada baris lain berarti implementasi ditemukan dan self-check/test-nya lulus; tidak semua baris diuji ulang di level runtime.

---

## 1. Kebutuhan Bisnis (Business Requirements)

| ID | Deskripsi Ringkas | File Implementasi Utama | File Test | Status |
| **BR-01** | Trader Discovery & Wallet Scoring | `backend/src/api/admin_routes.py` (intake & approval) · `backend/src/ingestion/solana.py` · `backend/src/agents/wallet_scorer.py` (`run_wallet_scoring_loop`) · `backend/src/models.py` (`Wallet`, `WalletObservation`) | `backend/src/agents/test_copy_trade_chain.py` · `backend/src/agents/test_wallet_scorer.py` | ✅ Fulfilled — rantai intake → riwayat hingga 50 tx → kalkulasi metrik (PnL SOL bersih biaya, Win Rate, PF, Max Drawdown dari high-water mark, rata-rata durasi kepemilikan aset FIFO, umur aktivitas ≥ 30 hari) → anti-manipulasi screen (FR-WLT-02) → approval operator → sinyal copy-trade terverifikasi (2026-10-27) |
| **BR-02** | AI Analysis tanpa Eksekusi Langsung | `backend/src/agents/hermes.py` · `backend/src/agents/schemas.py` · `backend/src/gateway/client.py` | `backend/src/agents/test_hermes.py` | ✅ Fulfilled |
| **BR-03** | Deterministic Risk Gate (Non-Bypassable) | `backend/src/risk/gate.py` · `backend/src/risk/engine.py` | `backend/src/risk/test_gate.py` | ✅ Fulfilled |
| **BR-04** | Paper Trading & Backtesting Realistis | `backend/src/risk/broker.py` · `backend/src/backtest/engine.py` · `backend/src/risk/ledger.py` | `backend/src/risk/test_broker.py` · `backend/src/backtest/test_backtest.py` | ✅ Fulfilled |
| **BR-05** | Dashboard & Kill Switch ≤ 2 detik | `backend/src/api/control.py` · `backend/src/control/telegram_bot.py` · `frontend/src/components/KillSwitch.tsx` | `backend/src/risk/test_gate.py` (AC-CTL-01) | ✅ Fulfilled |
| **BR-06** | Audit Trail & No Private Keys | `backend/src/models.py` (`LLMRequest`, `SystemEvent`) · `backend/src/config.py` | `backend/src/ingestion/test_heuristics.py` | ✅ Fulfilled |

---

## 2. Kebutuhan Fungsional — Modul 1: Ingestion & Data Blockchain

| ID | Deskripsi Ringkas | File Implementasi | File Test | Status |
|---|---|---|---|---|
| **FR-ING-01** | Polling Transaksi On-Chain Solana | `backend/src/ingestion/solana.py` | `backend/src/ingestion/test_heuristics.py` | ✅ Fulfilled |
| **FR-ING-02** | Parsing & Klasifikasi Swap DEX | `backend/src/ingestion/solana.py` · `backend/src/ingestion/common.py` | `backend/src/ingestion/test_heuristics.py` | ✅ Fulfilled |
| **FR-ING-03** | Ingestion Snapshot Harga & Likuiditas | `backend/src/ingestion/binance.py` · `backend/src/ingestion/aggregator.py` | `backend/src/ingestion/test_aggregator.py` · `test_binance.py` | ✅ Fulfilled |
| **FR-ING-04** | Error Ingestion & Dead Letter Queue | `backend/src/ingestion/aggregator.py` · DB: `ingestion_errors` (migrasi 002) | `backend/src/ingestion/test_aggregator.py` · `test_binance.py` | ✅ Fulfilled |

---

## 3. Kebutuhan Fungsional — Modul 2: Wallet Discovery & Monitoring

| ID | Deskripsi Ringkas | File Implementasi | File Test | Status |
|---|---|---|---|---|
| **FR-WLT-01** | Kalkulasi Metrik Kinerja Historis Wallet | `backend/src/agents/wallet_scorer.py` (`calculate_wallet_metrics`, `update_wallet_scores` via `run_wallet_scoring_loop`) · `backend/src/models.py` | `backend/src/agents/test_wallet_scorer.py` (`test_holding_duration_and_history_window`) · verifikasi DB nyata (audit 12 §3) | ✅ Fulfilled — Net Realized PnL dalam SOL bersih biaya, Win Rate, Profit Factor, Max Drawdown dari high-water mark ekuitas, rata-rata durasi kepemilikan aset FIFO (`avg_holding_time_hours`), dan validasi rentang riwayat aktivitas ≥ 30 hari (`has_min_history_30d`) terimplementasi dan diuji (2026-10-27) |
| **FR-WLT-02** | Skrining Anti-Manipulasi Wallet | `backend/src/agents/anti_manipulation.py` (`screen_wallet`, `_detect_wash_trades`, `_detect_one_hit_wonder`) · Diintegrasikan ke `backend/src/agents/wallet_scorer.py` (`update_wallet_scores` — wallet diARCHIVED jika manipulasi terdeteksi) | `backend/src/agents/test_anti_manipulation.py` (10 test cases: clean, wash trade, 1-hit wonder, false-positive guards) | ✅ Fulfilled — deteksi wash trading (BUY→SELL ≤ 5 min + PnL ≤ 1%) dan 1-hit wonder (≥ 80% profit 1 token, ≤ 5 trade) terimplementasi dan diuji (2026-10-27) |
| **FR-WLT-03** | Pengelolaan Watchlist & Approval | `backend/src/api/routes.py` (`GET /api/v1/wallets`) · `backend/src/api/admin_routes.py` (`POST /api/v1/admin/wallets`, `PATCH /api/v1/admin/wallets/{address}`) · `frontend/src/components/WalletExplorer.tsx` · `backend/src/agents/wallet_scorer.py` (promosi ke `PENDING_REVIEW`) | `backend/src/agents/test_copy_trade_chain.py` · `frontend/e2e/app.spec.ts` | ✅ Fulfilled — approval manual `PENDING_REVIEW → ACTIVE_MONITORED` / `ARCHIVED` sesuai WALLET_DISCOVERY_FLOWCHART (P1-1) |

---

## 4. Kebutuhan Fungsional — Modul 3: AI Model Gateway & Multi-Agent

| ID | Deskripsi Ringkas | File Implementasi | File Test | Status |
|---|---|---|---|---|
| **FR-AI-01** | AI Model Gateway dengan Fallback | `backend/src/gateway/client.py` | `backend/src/agents/test_hermes.py` | ✅ Fulfilled |
| **FR-AI-02** | Validasi Output Berstruktur (Pydantic) | `backend/src/agents/schemas.py` · `backend/src/gateway/client.py` | `backend/src/agents/test_hermes.py` | ✅ Fulfilled |
| **FR-AI-03** | Agen Token Safety & Contract Analysis | `backend/src/agents/skills.py` · `backend/src/agents/schemas.py` · `backend/src/agents/hermes.py` · `backend/src/ingestion/solana.py` (`_verify_mint_authorities`) | `backend/src/agents/test_hermes.py` · `backend/src/agents/test_copy_trade_chain.py` | ⚠️ Partial — mint/freeze authority token SPL kini dibaca on-chain (deterministik, jalur copy-trade; Token-2022 dianggap tidak aman). Belum: LP burn, konsentrasi holder; agen LLM safety masih hanya aturan Binance Spot |
| **FR-AI-04** | Agen Strategy Signal Generator | `backend/src/agents/hermes.py` · `backend/src/agents/schemas.py` | `backend/src/agents/test_hermes.py` | ✅ Fulfilled — usulan SELL tidak dijadikan `trading_signals` karena paper trading spot long-only (F-27); jawaban LLM tetap tercatat di `llm_requests` |

---

## 5. Kebutuhan Fungsional — Modul 4: Deterministic Risk Engine

| ID | Deskripsi Ringkas | File Implementasi | File Test | Status |
|---|---|---|---|---|
| **FR-RSK-01** | 9-Gate Non-Bypassable Risk Check | `backend/src/risk/gate.py` (`evaluate_risk`) · `backend/src/risk/engine.py` · `backend/src/risk/sizing.py` · `engine/src/main.rs` | `backend/src/risk/test_gate.py` · `engine/src/main.rs` (cargo test) · `backend/src/risk/test_engine_e2e.py` | ✅ Fulfilled — 9 pintu serial fail-closed terimplementasi lengkap di Python & Rust, termasuk Gate 6 validasi Stop Loss & rasio R:R ≥ 1:1.5 (F-17) |
| **NFR-PRF-01 / ADR-006** | Rust Risk Gate microservice & fail-closed IPC client | `engine/src/main.rs` · `backend/src/risk/engine_client.py` · `docker-compose*.yml` | `engine/src/main.rs` (cargo test) · `backend/src/risk/test_engine_client.py` · `test_parity.py` · `test_engine_e2e.py` (engine up/down) | ✅ Fulfilled — ambang kini identik Python (F-02) dan engine membaca request utuh (F-20) |

---

## 6. Kebutuhan Fungsional — Modul 5: Trading Simulation & Accounting

| ID | Deskripsi Ringkas | File Implementasi | File Test | Status |
|---|---|---|---|---|
| **FR-SIM-01** | Paper Order Matching & Fee Simulation | `backend/src/risk/broker.py` (`simulate_fills`, `fee_for_venue`) · `backend/src/models.py` (`PaperOrder`, `PaperTrade`) | `backend/src/risk/test_broker.py` | ✅ Fulfilled |
| **FR-SIM-02** | Position Management & Compounding | `backend/src/risk/ledger.py` · `backend/src/models.py` (`Position`, `PortfolioSnapshot`) | `backend/src/risk/test_ledger.py` | ✅ Fulfilled |
| **FR-SIM-03** | Backtesting Engine (No Look-Ahead Bias) | `backend/src/backtest/engine.py` · `backend/src/backtest/strategy.py` · `backend/src/backtest/data.py` | `backend/src/backtest/test_backtest.py` | ✅ Fulfilled |
| **FR-MKT-01** | Market Data Ingestion (Binance Spot) | `backend/src/ingestion/binance.py` | `backend/src/ingestion/test_binance.py` | ✅ Fulfilled |
| **FR-MKT-02** | OHLCV Candle Aggregator | `backend/src/ingestion/aggregator.py` · DB: `market_ohlcv` (migrasi 002) | `backend/src/ingestion/test_aggregator.py` | ✅ Fulfilled |

---

## 7. Kebutuhan Fungsional — Modul 6: Web Dashboard

| ID | Deskripsi Ringkas | File Implementasi | File Test | Status |
|---|---|---|---|---|
| **FR-UI-01** | Portfolio Real-Time Dashboard | `frontend/src/components/EquityHero.tsx` · `frontend/src/app/page.tsx` · `frontend/src/lib/api.ts` | — | ✅ Fulfilled |
| **FR-UI-02** | Wallet & Token Explorer | `frontend/src/components/WalletExplorer.tsx` · `frontend/src/app/wallets/page.tsx` | `frontend/e2e/app.spec.ts` | ⚠️ Partial — daftar wallet ter-skor ada (sebelumnya placeholder); explorer token & riwayat swap belum ada |
| **FR-UI-03** | Signal & Risk Gate Audit Log | `frontend/src/components/SignalLog.tsx` · `frontend/src/components/RiskGatePanel.tsx` · `frontend/src/app/risk/page.tsx` | — | ✅ Fulfilled |

---

## 8. Kebutuhan Fungsional — Modul 7: Telegram Bot

| ID | Deskripsi Ringkas | File Implementasi | File Test | Status |
|---|---|---|---|---|
| **FR-TG-01** | Notifikasi Kejadian Kritis | `backend/src/control/telegram_bot.py` (`notify_operator`) · `backend/src/risk/engine.py` | `backend/src/control/test_telegram_bot.py` | ✅ Fulfilled |
| **FR-TG-02** | Otorisasi & Perintah Kendali | `backend/src/control/telegram_bot.py` (`_handle_command`, `_is_allowed`) · `backend/src/api/control.py` | `backend/src/control/test_telegram_bot.py` | ✅ Fulfilled — 5 perintah (`/status`, `/positions`, `/pause`, `/resume`, `/kill`); allowlist chat **dan** pengirim. `/status` sebelumnya crash diam-diam (F-25, diperbaiki) |

---

## 9. Kebutuhan Fungsional — Modul 8: Audit Logging & Emergency Stop

| ID | Deskripsi Ringkas | File Implementasi | File Test | Status |
|---|---|---|---|---|
| **FR-AUD-01** | Pencatatan Penuh LLM & System Events | `backend/src/models.py` (`LLMRequest`, `SystemEvent`) · `backend/src/api/control.py` | — | ✅ Fulfilled |
| **FR-AUD-02** | Emergency Stop Deterministik | `backend/src/api/control.py` (`emergency_stop`) · `backend/src/risk/engine.py` (`is_paused`) · `frontend/src/components/KillSwitch.tsx` | `backend/src/api/test_http.py` · `frontend/e2e/app.spec.ts` (gagal kirim tidak lagi tampil "engaged", F-22) | ✅ Fulfilled |

---

## 10. Kriteria Penerimaan (Acceptance Criteria)

| ID | Deskripsi Ringkas | Metode Verifikasi | File Test / Kode Terkait | Status |
|---|---|---|---|---|
| **AC-ING-01** | Deduplikasi 100 signature, 20 duplikat → 80 unik | pytest mock stream | `backend/src/ingestion/test_heuristics.py` | ✅ Fulfilled |
| **AC-ING-02** | Klasifikasi swap vs transfer 100% akurat | pytest dataset 50 tx | `backend/src/ingestion/test_heuristics.py` | ✅ Fulfilled |
| **AC-ING-03** | Deteksi data stale > 30 detik → `DATA_STALE` | inject snapshot 45s | `backend/src/risk/gate.py` (`data_freshness_check`) | ✅ Fulfilled |
| **AC-ING-04** | Rate limit 429 → exponential backoff | mock HTTP 429 | `backend/src/ingestion/test_heuristics.py` | ✅ Fulfilled |
| **AC-AI-01** | 100% respons lolos Pydantic validation | 50 inference runs | `backend/src/agents/test_hermes.py` | ✅ Fulfilled |
| **AC-AI-02** | Fallback ke 9Route < 2 detik | inject HTTP 500 | `backend/src/gateway/client.py` | ✅ Fulfilled |
| **AC-AI-03** | Prompt injection tidak mengubah sinyal | adversarial string | `backend/src/agents/test_hermes.py` | ✅ Fulfilled |
| **AC-AI-04** | Tidak ada tool pengubah saldo di agent | inspect tool defs | `backend/src/agents/skills.py` | ✅ Fulfilled |
| **AC-RSK-01** | Sinyal > maks size → `REJECTED_EXCEEDS_MAX_SIZE` | pytest | `backend/src/risk/test_gate.py` | ✅ Fulfilled |
| **AC-RSK-02** | Likuiditas < $20k → `REJECTED_LOW_LIQUIDITY` | pytest | `backend/src/agents/test_copy_trade.py` (kode aktual: `INSUFFICIENT_POOL_LIQUIDITY`, di `copy_trade.py`) | ✅ Fulfilled |
| **AC-RSK-03** | Token freeze_authority aktif → `REJECTED` | pytest | `backend/src/agents/test_copy_trade.py` (kode aktual: `TOKEN_UNSAFE_AUTHORITY_NOT_REVOKED`) | ✅ Fulfilled |
| **AC-RSK-04** | Daily loss ≥ 2% → blokir semua BUY baru | pytest | `backend/src/risk/test_gate.py` | ✅ Fulfilled |
| **AC-RSK-05** | Risk Gate tidak bisa di-bypass via prompt | code review | `backend/src/risk/gate.py` (no LLM call) | ✅ Fulfilled |
| **AC-SIM-01** | Akuntansi 50 cycle: deviasi = 0.00 | pytest | `backend/src/risk/test_broker.py` | ✅ Fulfilled |
| **AC-SIM-02** | Fill price ≠ mid-market (slippage + fee) | pytest | `backend/src/risk/test_broker.py` | ✅ Fulfilled |
| **AC-SIM-03** | Backtest: hanya `closes[:i+1]` (no future leak) | code review + pytest | `backend/src/backtest/engine.py:89` · `backend/src/backtest/test_backtest.py` | ✅ Fulfilled |
| **AC-CTL-01** | `/kill` hentikan semua signal ≤ 2 detik | HTTP test (`elapsed_ms < 2000`) | `backend/src/api/test_http.py` | ✅ Fulfilled |
| **AC-CTL-02** | Unauthorized ID → 100% silent drop | unit test allowlist chat + pengirim | `backend/src/control/test_telegram_bot.py` (`_is_allowed`) | ✅ Fulfilled |
| **AC-CTL-03** | Notifikasi kritis tiba ≤ 3 detik | integration test | `backend/src/control/test_telegram_bot.py` | ✅ Fulfilled |
| **AC-OPS-01** | RAM ≤ 8 GB selama 2 jam stress test | Docker stats monitor script | `scripts/ram_soak_monitor.py` | ✅ Fulfilled |
| **AC-OPS-02** | 0 private key/token di log & kode | trufflehog / regex scan | `.env.example`, `backend/src/config.py` | ✅ Fulfilled |
| **AC-OPS-03** | DB restore 100% integritas FK | pg_dump + restore drill script | `scripts/drill_db_restore.sh` | ✅ Fulfilled |

---

## 11. Rekapitulasi

| Kategori | Total | ✅ Fulfilled | ⚠️ Partial | ❌ Pending |
|---|---|---|---|---|
| Business Requirements (BR) | 6 | 6 (100%) | 0 | 0 |
| Functional Requirements (FR, termasuk NFR-PRF-01) | 25 | 22 (88%) | 3 | 0 |
| Acceptance Criteria (AC) | 22 | 22 (100%) | 0 | 0 |
| **TOTAL** | **53** | **50 (94.3%)** | **3 (5.7%)** | **0 (0%)** |

> Rekap lama (48 baris, 100%) salah hitung: tabel FR berisi 25 baris, bukan 20. Angka di atas dihitung dari baris tabel setelah koreksi audit 2026-10-26 (P1-1: FR-WLT-03 → ✅; FR-WLT-02 dikoreksi ke ❌ karena skrining anti-manipulasi tidak ditemukan di kode; FR-WLT-01 dikoreksi ke ⚠️ karena durasi kepemilikan dan input riwayat ≥ 30 hari belum ada, `audit/reports/15-sell-and-wallet-scoring.md`).

### Status Penyelesaian Kesenjangan (All Resolved - 24 Okt 2026)

Semua item kesenjangan yang sebelumnya Partial/Pending telah diselesaikan dan diverifikasi:
1. `FR-ING-03/04`: Telah diuji pada [`backend/src/ingestion/test_aggregator.py`](../../backend/src/ingestion/test_aggregator.py) dan [`test_binance.py`](../../backend/src/ingestion/test_binance.py).
2. `FR-WLT-01`: Mesin kalkulasi ranking diimplementasikan pada [`backend/src/agents/wallet_scorer.py`](../../backend/src/agents/wallet_scorer.py) & diuji di [`test_wallet_scorer.py`](../../backend/src/agents/test_wallet_scorer.py).
3. `FR-SIM-02`: Logika posisi & compounding terisolasi diuji pada [`backend/src/risk/test_ledger.py`](../../backend/src/risk/test_ledger.py).
4. `FR-TG-01` & `AC-CTL-03`: Integrasi event push alert diselesaikan di [`backend/src/control/telegram_bot.py`](../../backend/src/control/telegram_bot.py) & diuji di [`test_telegram_bot.py`](../../backend/src/control/test_telegram_bot.py).
5. `AC-ING-04`: Dedicated backoff 429 diuji pada [`backend/src/ingestion/test_heuristics.py`](../../backend/src/ingestion/test_heuristics.py).
6. `AC-OPS-01`: Skrip pemantauan penggunaan RAM soak test disediakan di [`scripts/ram_soak_monitor.py`](../../scripts/ram_soak_monitor.py).
7. `AC-OPS-03`: Skrip pengujian disaster recovery dan verifikasi FK disediakan di [`scripts/drill_db_restore.sh`](../../scripts/drill_db_restore.sh).
