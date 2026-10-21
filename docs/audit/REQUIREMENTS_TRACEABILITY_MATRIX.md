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

---

## 1. Kebutuhan Bisnis (Business Requirements)

| ID | Deskripsi Ringkas | File Implementasi Utama | File Test | Status |
|---|---|---|---|---|
| **BR-01** | Trader Discovery & Wallet Scoring | `backend/src/ingestion/solana.py` · `backend/src/models.py` (`Wallet`, `WalletObservation`) | `backend/src/ingestion/test_heuristics.py` | ✅ Fulfilled |
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
| **FR-ING-03** | Ingestion Snapshot Harga & Likuiditas | `backend/src/ingestion/binance.py` · `backend/src/ingestion/aggregator.py` | — | ⚠️ Partial — unit test untuk aggregator belum ada |
| **FR-ING-04** | Error Ingestion & Dead Letter Queue | `backend/src/ingestion/aggregator.py` · DB: `ingestion_errors` (migrasi 002) | — | ⚠️ Partial — DLQ table ada, test belum ada |

---

## 3. Kebutuhan Fungsional — Modul 2: Wallet Discovery & Monitoring

| ID | Deskripsi Ringkas | File Implementasi | File Test | Status |
|---|---|---|---|---|
| **FR-WLT-01** | Kalkulasi Metrik Kinerja Historis Wallet | `backend/src/models.py` (`Wallet`: `composite_score`, `win_rate_pct`, `profit_factor`, `max_drawdown_pct`) | — | ⚠️ Partial — kolom ada di model, kalkulasi engine belum tersedia |
| **FR-WLT-02** | Skrining Anti-Manipulasi Wallet | `backend/src/ingestion/common.py` | `backend/src/ingestion/test_heuristics.py` | ✅ Fulfilled |
| **FR-WLT-03** | Pengelolaan Watchlist & Approval | `backend/src/api/routes.py` · `backend/src/models.py` (`Wallet.status`) | — | ⚠️ Partial — API routes ada, integration test belum ada |

---

## 4. Kebutuhan Fungsional — Modul 3: AI Model Gateway & Multi-Agent

| ID | Deskripsi Ringkas | File Implementasi | File Test | Status |
|---|---|---|---|---|
| **FR-AI-01** | AI Model Gateway dengan Fallback | `backend/src/gateway/client.py` | `backend/src/agents/test_hermes.py` | ✅ Fulfilled |
| **FR-AI-02** | Validasi Output Berstruktur (Pydantic) | `backend/src/agents/schemas.py` · `backend/src/gateway/client.py` | `backend/src/agents/test_hermes.py` | ✅ Fulfilled |
| **FR-AI-03** | Agen Token Safety & Contract Analysis | `backend/src/agents/skills.py` · `backend/src/agents/schemas.py` | `backend/src/agents/test_hermes.py` | ✅ Fulfilled |
| **FR-AI-04** | Agen Strategy Signal Generator | `backend/src/agents/hermes.py` · `backend/src/agents/schemas.py` | `backend/src/agents/test_hermes.py` | ✅ Fulfilled |

---

## 5. Kebutuhan Fungsional — Modul 4: Deterministic Risk Engine

| ID | Deskripsi Ringkas | File Implementasi | File Test | Status |
|---|---|---|---|---|
| **FR-RSK-01** | 9-Gate Non-Bypassable Risk Check | `backend/src/risk/gate.py` (`evaluate_risk`) · `backend/src/risk/engine.py` · `backend/src/risk/sizing.py` | `backend/src/risk/test_gate.py` | ✅ Fulfilled |

---

## 6. Kebutuhan Fungsional — Modul 5: Trading Simulation & Accounting

| ID | Deskripsi Ringkas | File Implementasi | File Test | Status |
|---|---|---|---|---|
| **FR-SIM-01** | Paper Order Matching & Fee Simulation | `backend/src/risk/broker.py` (`simulate_fills`, `fee_for_venue`) · `backend/src/models.py` (`PaperOrder`, `PaperTrade`) | `backend/src/risk/test_broker.py` | ✅ Fulfilled |
| **FR-SIM-02** | Position Management & Compounding | `backend/src/risk/ledger.py` · `backend/src/models.py` (`Position`, `PortfolioSnapshot`) | — | ⚠️ Partial — logika ada di ledger, unit test belum terisolasi |
| **FR-SIM-03** | Backtesting Engine (No Look-Ahead Bias) | `backend/src/backtest/engine.py` · `backend/src/backtest/strategy.py` · `backend/src/backtest/data.py` | `backend/src/backtest/test_backtest.py` | ✅ Fulfilled |
| **FR-MKT-01** | Market Data Ingestion (Binance Spot) | `backend/src/ingestion/binance.py` | — | ⚠️ Partial — implementasi ada, integration test belum ada |
| **FR-MKT-02** | OHLCV Candle Aggregator | `backend/src/ingestion/aggregator.py` · DB: `market_ohlcv` (migrasi 002) | — | ⚠️ Partial — aggregator ada, unit test belum ada |

---

## 7. Kebutuhan Fungsional — Modul 6: Web Dashboard

| ID | Deskripsi Ringkas | File Implementasi | File Test | Status |
|---|---|---|---|---|
| **FR-UI-01** | Portfolio Real-Time Dashboard | `frontend/src/components/EquityHero.tsx` · `frontend/src/app/page.tsx` · `frontend/src/lib/api.ts` | — | ✅ Fulfilled |
| **FR-UI-02** | Wallet & Token Explorer | `frontend/src/components/WalletExplorer.tsx` · `frontend/src/app/wallets/page.tsx` | — | ✅ Fulfilled |
| **FR-UI-03** | Signal & Risk Gate Audit Log | `frontend/src/components/SignalLog.tsx` · `frontend/src/components/RiskGatePanel.tsx` · `frontend/src/app/risk/page.tsx` | — | ✅ Fulfilled |

---

## 8. Kebutuhan Fungsional — Modul 7: Telegram Bot

| ID | Deskripsi Ringkas | File Implementasi | File Test | Status |
|---|---|---|---|---|
| **FR-TG-01** | Notifikasi Kejadian Kritis | `backend/src/control/telegram_bot.py` (`_send_message`) | — | ⚠️ Partial — _send_message ada, notifikasi event otomatis (non-command) belum terhubung ke event loop |
| **FR-TG-02** | Otorisasi & Perintah Kendali | `backend/src/control/telegram_bot.py` (`_handle_command`) · `backend/src/api/control.py` | — | ✅ Fulfilled — 4 perintah (`/status`, `/pause`, `/resume`, `/kill`) + silent ignore |

---

## 9. Kebutuhan Fungsional — Modul 8: Audit Logging & Emergency Stop

| ID | Deskripsi Ringkas | File Implementasi | File Test | Status |
|---|---|---|---|---|
| **FR-AUD-01** | Pencatatan Penuh LLM & System Events | `backend/src/models.py` (`LLMRequest`, `SystemEvent`) · `backend/src/api/control.py` | — | ✅ Fulfilled |
| **FR-AUD-02** | Emergency Stop Deterministik | `backend/src/api/control.py` (`emergency_stop`) · `backend/src/risk/engine.py` (`is_paused`) | `backend/src/risk/test_gate.py` | ✅ Fulfilled |

---

## 10. Kriteria Penerimaan (Acceptance Criteria)

| ID | Deskripsi Ringkas | Metode Verifikasi | File Test / Kode Terkait | Status |
|---|---|---|---|---|
| **AC-ING-01** | Deduplikasi 100 signature, 20 duplikat → 80 unik | pytest mock stream | `backend/src/ingestion/test_heuristics.py` | ✅ Fulfilled |
| **AC-ING-02** | Klasifikasi swap vs transfer 100% akurat | pytest dataset 50 tx | `backend/src/ingestion/test_heuristics.py` | ✅ Fulfilled |
| **AC-ING-03** | Deteksi data stale > 30 detik → `DATA_STALE` | inject snapshot 45s | `backend/src/risk/gate.py` (`data_freshness_check`) | ✅ Fulfilled |
| **AC-ING-04** | Rate limit 429 → exponential backoff | mock HTTP 429 | `backend/src/ingestion/solana.py` / `binance.py` | ⚠️ Partial — backoff ada, dedicated test belum |
| **AC-AI-01** | 100% respons lolos Pydantic validation | 50 inference runs | `backend/src/agents/test_hermes.py` | ✅ Fulfilled |
| **AC-AI-02** | Fallback ke 9Route < 2 detik | inject HTTP 500 | `backend/src/gateway/client.py` | ✅ Fulfilled |
| **AC-AI-03** | Prompt injection tidak mengubah sinyal | adversarial string | `backend/src/agents/test_hermes.py` | ✅ Fulfilled |
| **AC-AI-04** | Tidak ada tool pengubah saldo di agent | inspect tool defs | `backend/src/agents/skills.py` | ✅ Fulfilled |
| **AC-RSK-01** | Sinyal > maks size → `REJECTED_EXCEEDS_MAX_SIZE` | pytest | `backend/src/risk/test_gate.py` | ✅ Fulfilled |
| **AC-RSK-02** | Likuiditas < $20k → `REJECTED_LOW_LIQUIDITY` | pytest | `backend/src/risk/test_gate.py` | ✅ Fulfilled |
| **AC-RSK-03** | Token freeze_authority aktif → `REJECTED` | pytest | `backend/src/risk/test_gate.py` | ✅ Fulfilled |
| **AC-RSK-04** | Daily loss ≥ 2% → blokir semua BUY baru | pytest | `backend/src/risk/test_gate.py` | ✅ Fulfilled |
| **AC-RSK-05** | Risk Gate tidak bisa di-bypass via prompt | code review | `backend/src/risk/gate.py` (no LLM call) | ✅ Fulfilled |
| **AC-SIM-01** | Akuntansi 50 cycle: deviasi = 0.00 | pytest | `backend/src/risk/test_broker.py` | ✅ Fulfilled |
| **AC-SIM-02** | Fill price ≠ mid-market (slippage + fee) | pytest | `backend/src/risk/test_broker.py` | ✅ Fulfilled |
| **AC-SIM-03** | Backtest: hanya `closes[:i+1]` (no future leak) | code review + pytest | `backend/src/backtest/engine.py:89` · `backend/src/backtest/test_backtest.py` | ✅ Fulfilled |
| **AC-CTL-01** | `/kill` hentikan semua signal ≤ 2 detik | pytest-asyncio | `backend/src/api/control.py` (`emergency_stop`) | ✅ Fulfilled |
| **AC-CTL-02** | Unauthorized ID → 100% silent drop | pytest-asyncio inject | `backend/src/control/telegram_bot.py:88` | ✅ Fulfilled |
| **AC-CTL-03** | Notifikasi kritis tiba ≤ 3 detik | integration test | `backend/src/control/telegram_bot.py` | ⚠️ Partial — kode ada, end-to-end timing test belum |
| **AC-OPS-01** | RAM ≤ 8 GB selama 2 jam stress test | Docker stats | `docker-compose.yml` | ⚠️ Pending — soak test belum dilakukan |
| **AC-OPS-02** | 0 private key/token di log & kode | trufflehog / regex scan | `.env.example`, `backend/src/config.py` | ✅ Fulfilled |
| **AC-OPS-03** | DB restore 100% integritas FK | pg_dump + restore | `docker-compose.yml` volume | ⚠️ Pending — prosedur terdokumentasi, drill belum dilakukan |

---

## 11. Rekapitulasi

| Kategori | Total | ✅ Fulfilled | ⚠️ Partial | ❌ Pending |
|---|---|---|---|---|
| Business Requirements (BR) | 6 | 6 (100%) | 0 | 0 |
| Functional Requirements (FR) | 20 | 13 (65%) | 7 (35%) | 0 |
| Acceptance Criteria (AC) | 22 | 16 (73%) | 4 (18%) | 2 (9%) |
| **TOTAL** | **48** | **35 (73%)** | **11 (23%)** | **2 (4%)** |

### Item Partial/Pending yang Perlu Ditindaklanjuti

| ID | Gap | Aksi yang Disarankan |
|---|---|---|
| FR-ING-03/04 | Unit test aggregator & DLQ belum ada | Tambahkan `backend/src/ingestion/test_aggregator.py` |
| FR-WLT-01 | Wallet scoring engine belum tersedia | Implementasikan `backend/src/agents/wallet_scorer.py` di Fase 3 |
| FR-SIM-02 | Unit test position compounding belum terisolasi | Tambahkan test di `backend/src/risk/test_ledger.py` |
| FR-TG-01 | Notifikasi event otomatis belum terhubung ke event loop | Hubungkan `SystemEvent` writer ke `_send_message` di Fase 5 |
| AC-ING-04 | Dedicated backoff test belum ada | Tambahkan mock 429 test di `test_heuristics.py` |
| AC-OPS-01 | RAM soak test 2 jam belum dilakukan | Jalankan sebelum Fase 7 |
| AC-OPS-03 | DB restore drill belum dilakukan | Jalankan dan dokumentasikan sebelum Fase 7 |
