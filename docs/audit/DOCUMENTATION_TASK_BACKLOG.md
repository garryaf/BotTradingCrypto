# DOCUMENTATION TASK BACKLOG
**Proyek:** AI Crypto Trading & Copy-Trading Platform (AUTO-TRADE-AA)  
**Dokumen:** `docs/audit/DOCUMENTATION_TASK_BACKLOG.md`  
**Status Audit:** READ-ONLY AUDIT BASELINE  
**Tanggal:** 21 Oktober 2026  

---

## 1. Ringkasan Backlog Tugas Dokumentasi

Berdasarkan audit komprehensif terhadap dokumen spesifikasi (`docs/`), artefak diagram (`docs/03-diagrams/`), dan implementasi kode aktual (`backend/`, `frontend/`, `engine/`), ditemukan **8 kesenjangan (gaps) dan ketidaksinkronan nyata** antara dokumen dan implementasi. Seluruh temuan ini dikonversi menjadi task dokumentasi yang terstruktur, dapat diverifikasi (*verifiable*), dan dapat dilacak (*traceable*).

### Distribusi Tugas Berdasarkan Prioritas
- **P0 (Urgent — Keamanan/Integritas):** 1 Task
- **P1 (High — Bisnis/Operasional/Arsitektur):** 3 Task
- **P2 (Medium — Kejelasan Kebutuhan/Konsistensi):** 3 Task
- **P3 (Low — Pemeliharaan & Detail UI/UX):** 1 Task
- **Total Task:** **8 Task**

### Distribusi Tugas Berdasarkan Kategori
- **A. Missing Documentation:** 1 Task
- **B. Outdated Documentation:** 1 Task
- **C. Inconsistent Documentation:** 2 Task
- **E. Business Process Documentation:** 1 Task
- **G. Technical Documentation:** 1 Task
- **I. Testing Documentation:** 1 Task
- **J. Operational Documentation:** 1 Task

---

## 2. Daftar Tugas Dokumentasi (Dikelompokkan Berdasarkan Prioritas)

### [P0 — URGENT]

#### DOC-TASK-001: Dokumentasi Prosedur Operasional & Reset State Circuit Breaker 4-Layer
- **Task ID:** `DOC-TASK-001`
- **Task Title:** Dokumentasi Prosedur Operasional, State Transitions, dan Reset Manual Circuit Breaker
- **Category:** `E. Business Process Documentation` / `J. Operational Documentation`
- **Priority:** `P0`
- **Status:** `DONE`
- **Completion Date:** 21 Oktober 2026
- **Description:**  
  Menyusun dokumen prosedur operasional standar (SOP) untuk penanganan 4 pemicu Circuit Breaker (Daily Loss $\ge 2\%$, Drawdown $\ge 8\%$, Data Stale $> 30$s, Anomali Slippage) serta mendokumentasikan mekanisme pemulihan manual (*recovery/reset procedure*) pasca-pembekuan sistem.
- **Reason for the task:**  
  Menyediakan panduan runbook operasional formal yang memastikan operator melakukan verifikasi portofolio dan mengikuti prosedur rilis terkontrol sebelum memanggil `/control/resume` atau `/confirm_reset_circuit`.
- **Related Audit Finding IDs:** `AUDIT-FINDING-01`
- **Related Requirement/Rule IDs:** `BR-RSK-03` (Daily Loss Limit), `BR-RSK-04` (Drawdown Limit), `AC-RSK-04`
- **Existing Document References:**  
  - [CIRCUIT_BREAKER_OPERATIONAL_SOP.md](file:///Users/nabilartanabil/SourceCode/AUTO-TRADE-AA/docs/05-security/CIRCUIT_BREAKER_OPERATIONAL_SOP.md)
  - [FAILURE_MODES_AND_RECOVERY.md](file:///Users/nabilartanabil/SourceCode/AUTO-TRADE-AA/docs/02-architecture/FAILURE_MODES_AND_RECOVERY.md#L38)
  - [ARCHITECTURE_REVIEW_AND_ALIGNMENT.md](file:///Users/nabilartanabil/SourceCode/AUTO-TRADE-AA/docs/00-overview/ARCHITECTURE_REVIEW_AND_ALIGNMENT.md#L50)
  - [backend/src/risk/gate.py](file:///Users/nabilartanabil/SourceCode/AUTO-TRADE-AA/backend/src/risk/gate.py)
  - [backend/src/api/control.py](file:///Users/nabilartanabil/SourceCode/AUTO-TRADE-AA/backend/src/api/control.py)
- **Expected Deliverable:**  
  File baru `docs/05-security/CIRCUIT_BREAKER_OPERATIONAL_SOP.md` dan pembaruan mendalam pada `docs/02-architecture/FAILURE_MODES_AND_RECOVERY.md`. **[TERLAKSANA]**
- **Scope:**  
  Alur pembekuan, state machine transisi (`ACTIVE`, `PAUSED`, `FROZEN`, `EMERGENCY_STOPPED`, `PENDING_REVIEW`), parameter validasi reset, checklist audit pra-resume 10 butir, dan interaksi command bot Telegram `/resume` & `/confirm_reset_circuit`.
- **Dependencies:** Tidak ada.
- **Acceptance Criteria:**  
  1. Keempat skenario pemicu Circuit Breaker didokumentasikan dengan kondisi input numerik yang terdefinisi. **[TERPENUHI]**
  2. Diagram alur transisi state status sistem (`ACTIVE`, `PAUSED`, `FROZEN`, `EMERGENCY_STOPPED`, `PENDING_REVIEW`) terdokumentasi lengkap. **[TERPENUHI]**
  3. Prosedur rilis/unfreeze manual operator melalui API `/control/resume` dan Telegram didokumentasikan langkah demi langkah. **[TERPENUHI]**
  4. Checklist keselamatan pra-resume mencakup audit posisi terbuka, verifikasi saldo kas, dan verifikasi kestabilan data feed. **[TERPENUHI]**
- **Verification Method:**  
  Review silang terhadap kode `backend/src/api/control.py` dan `backend/src/risk/gate.py` memastikan setiap field status cocok 1:1.
- **Assumptions or Unresolved Questions:**  
  *Terselesaikan:* Reset drawdown $\ge 8\%$ mewajibkan 2-Step Confirmation via Telegram (`/resume` lalu ketik `/confirm_reset_circuit` dalam 60 detik) atau otorisasi token rahasia dengan flag `force_drawdown_reset: true` pada REST API.

---

### [P1 — HIGH]

#### DOC-TASK-002: Penyelarasan Nomenklatur Venue Bursa (Binance vs Bybit) Lintas Dokumen
- **Task ID:** `DOC-TASK-002`
- **Task Title:** Penyelarasan Inkonsistensi Nomenklatur Exchange Spot (Binance Spot vs Bybit Spot)
- **Category:** `C. Inconsistent Documentation`
- **Priority:** `P1`
- **Status:** `DONE`
- **Completion Date:** 21 Oktober 2026
- **Description:**  
  Mengaudit dan menyelaraskan penyebutan nama bursa terpusat (CEX) di seluruh dokumen arsitektur, kamus data, diagram, dan spesifikasi API dengan kebijakan multi-venue resmi: **Binance Spot** sebagai bursa primer aktif (MVP) dan **Bybit Spot** dipertahankan sebagai bursa sekunder untuk rilis mendatang (*future roadmap*).
- **Reason for the task:**  
  Menghilangkan ambiguitas antara implementasi kode aktual (`backend/src/ingestion/binance.py`, `frontend/src/lib/binance.ts`) dan blueprint dokumen terdahulu dengan menetapkan hierarki bursa CEX yang jelas dan terstruktur.
- **Related Audit Finding IDs:** `AUDIT-FINDING-02`
- **Related Requirement/Rule IDs:** `FR-MKT-01`, `ADR-005`
- **Existing Document References:**  
  - [OPEN_QUESTIONS.md](file:///Users/nabilartanabil/SourceCode/AUTO-TRADE-AA/docs/00-overview/OPEN_QUESTIONS.md#L16)
  - [ARCHITECTURE_OVERVIEW.md](file:///Users/nabilartanabil/SourceCode/AUTO-TRADE-AA/docs/02-architecture/ARCHITECTURE_OVERVIEW.md#L81)
  - [SYSTEM_CONTEXT.md](file:///Users/nabilartanabil/SourceCode/AUTO-TRADE-AA/docs/02-architecture/SYSTEM_CONTEXT.md#L45)
  - [DATA_DICTIONARY.md](file:///Users/nabilartanabil/SourceCode/AUTO-TRADE-AA/docs/04-data/DATA_DICTIONARY.md#L20)
  - [ERD.mmd](file:///Users/nabilartanabil/SourceCode/AUTO-TRADE-AA/docs/03-diagrams/ERD.mmd#L29)
  - [SYSTEM_CONTEXT.mmd](file:///Users/nabilartanabil/SourceCode/AUTO-TRADE-AA/docs/03-diagrams/SYSTEM_CONTEXT.mmd#L28)
  - [COMPONENT_DIAGRAM.mmd](file:///Users/nabilartanabil/SourceCode/AUTO-TRADE-AA/docs/03-diagrams/COMPONENT_DIAGRAM.mmd#L41)
  - [FUNCTIONAL_REQUIREMENTS.md](file:///Users/nabilartanabil/SourceCode/AUTO-TRADE-AA/docs/01-requirements/FUNCTIONAL_REQUIREMENTS.md#L116)
  - [SECRET_MANAGEMENT.md](file:///Users/nabilartanabil/SourceCode/AUTO-TRADE-AA/docs/05-security/SECRET_MANAGEMENT.md#L35)
  - [.env.example](file:///Users/nabilartanabil/SourceCode/AUTO-TRADE-AA/.env.example#L40)
  - [backend/src/ingestion/binance.py](file:///Users/nabilartanabil/SourceCode/AUTO-TRADE-AA/backend/src/ingestion/binance.py)
- **Expected Deliverable:**  
  Pembaruan tersinkronisasi pada `docs/00-overview/OPEN_QUESTIONS.md`, `docs/02-architecture/ARCHITECTURE_OVERVIEW.md`, `docs/02-architecture/SYSTEM_CONTEXT.md`, `docs/04-data/DATA_DICTIONARY.md`, `.env.example`, dan artefak diagram terkait.
- **Scope:**  
  Penyelarasan nomenklatur dual-venue (Binance Primer + Bybit Sekunder), endpoint API URL, format enum database (`binance_spot`, `bybit_spot`, `BINANCE_SPOT_SIM`, `BYBIT_SPOT_SIM`), konfigurasi environment variable, dan fee model (0.10% Taker fee).
- **Dependencies:** Tidak ada.
- **Acceptance Criteria:**  
  1. Seluruh dokumen di direktori `docs/` menggunakan referensi bursa CEX yang seragam dan konsisten: Binance Spot (Primer Aktif MVP) dan Bybit Spot (Sekunder Roadmap). **[TERPENUHI]**
  2. Tabel referensi `tokens.chain` dan `paper_trades.execution_venue` di `DATA_DICTIONARY.md` dan `ERD.mmd` diselaraskan dengan standar lowercase snake_case dan UPPERCASE constants. **[TERPENUHI]**
  3. Dokumen `.env.example` dan `SECRET_MANAGEMENT.md` menyediakan konfigurasi `BINANCE_*` aktif dan template `BYBIT_*` sekunder yang terverifikasi. **[TERPENUHI]**
- **Verification Method:**  
  Audit silang dan grep search repositori menunjukkan zero kontradiksi dan referensi bursa terstruktur secara harmonis di seluruh 10 file arsitektur dan konfigurasi.
- **Assumptions or Unresolved Questions:**  
  *Terselesaikan:* Bybit dipertahankan sebagai bursa sekunder untuk rilis mendatang (multi-venue & cross-exchange execution), sedangkan Binance Spot adalah bursa primer aktif untuk MVP saat ini.

---

#### DOC-TASK-003: Pembaruan Kamus Data & Model Relasional untuk Tabel DLQ dan OHLCV
- **Task ID:** `DOC-TASK-003`
- **Task Title:** Pembaruan DATA_MODEL.md dan DATA_DICTIONARY.md untuk Tabel `ingestion_errors` dan `market_ohlcv`
- **Category:** `B. Outdated Documentation` / `K. Documentation-to-Code Traceability`
- **Priority:** `P1`
- **Status:** `DONE`
- **Completion Date:** 21 Oktober 2026
- **Description:**  
  Memperbarui `DATA_MODEL.md`, `DATA_DICTIONARY.md`, dan diagram `ERD.mmd` agar mencerminkan evolusi skema migrasi database `002_ingestion_dlq_and_ohlcv.py` dan `003_risk_checks_max_positions.py`.
- **Reason for the task:**  
  Tabel `ingestion_errors` (Dead Letter Queue) dan `market_ohlcv` (agregasi time-series) telah dibuat di database melalui migrasi Alembic dan digunakan aktif oleh `aggregator.py`, namun kedua tabel ini belum tercatat pada dokumen arsitektur data resmi (`DATA_MODEL.md` dan `DATA_DICTIONARY.md`). Hal ini menciptakan kesenjangan dokumentasi skema (*schema drift*).
- **Related Audit Finding IDs:** `AUDIT-FINDING-03`
- **Related Requirement/Rule IDs:** `FR-ING-04` (Error Ingestion & DLQ), `FR-MKT-02` (Candle Aggregator)
- **Existing Document References:**  
  - [DATA_MODEL.md](file:///Users/nabilartanabil/SourceCode/AUTO-TRADE-AA/docs/04-data/DATA_MODEL.md)
  - [DATA_DICTIONARY.md](file:///Users/nabilartanabil/SourceCode/AUTO-TRADE-AA/docs/04-data/DATA_DICTIONARY.md)
  - [backend/alembic/versions/002_ingestion_dlq_and_ohlcv.py](file:///Users/nabilartanabil/SourceCode/AUTO-TRADE-AA/backend/alembic/versions/002_ingestion_dlq_and_ohlcv.py)
  - [backend/alembic/versions/003_risk_checks_max_positions.py](file:///Users/nabilartanabil/SourceCode/AUTO-TRADE-AA/backend/alembic/versions/003_risk_checks_max_positions.py)
- **Expected Deliverable:**  
  Seksi baru pada `DATA_DICTIONARY.md` untuk tabel `ingestion_errors` dan `market_ohlcv`, serta pembaruan definisi kolom `risk_checks.max_positions_check`.
- **Scope:**  
  Struktur kolom, tipe data, nullable constraint, foreign key, index, dan contoh nilai untuk kedua tabel baru.
- **Dependencies:** Tidak ada.
- **Acceptance Criteria:**  
  1. Tabel `ingestion_errors` terdokumentasi lengkap (id, error_type, raw_payload, error_message, ingested_at).
  2. Tabel `market_ohlcv` terdokumentasi lengkap (id, token_id, interval, open, high, low, close, volume, bucket_time).
  3. Kolom `max_positions_check` tercatat pada definisi tabel `risk_checks`.
  4. File `ERD.mmd` diperbarui memuat kedua entitas baru dan relasinya ke `tokens`.
- **Verification Method:**  
  Pengecekan skema tabel database aktual PostgreSQL via `\d ingestion_errors` dan `\d market_ohlcv` mencocokkan baris per baris.
- **Assumptions or Unresolved Questions:** Tidak ada.

---

#### DOC-TASK-004: Spesifikasi Integrasi & Batas Tanggung Jawab Core Engine Rust ([ADR-006](file:///Users/nabilartanabil/SourceCode/AUTO-TRADE-AA/docs/02-architecture/adr/ADR-006-hybrid-python-rust-architecture.md))
- **Task ID:** `DOC-TASK-004`
- **Task Title:** Dokumentasi Spesifikasi Arsitektur Integrasi Rust Engine dan FastAPI Backend
- **Category:** `G. Technical Documentation`
- **Priority:** `P1`
- **Status:** `DONE`
- **Completion Date:** 21 Oktober 2026
- **Description:**  
  Mendokumentasikan mekanisme komunikasi, batas tanggung jawab (*boundary responsibility*), dan protokol interoperabilitas antara Core High-Speed Engine berbasis Rust (`engine/`) dengan Python FastAPI (`backend/`).

  ADR-006 menetapkan arsitektur Hibrida Python + Rust, dan modul Rust (`engine/src/risk_gate/mod.rs`) telah terbukti mampu mengevaluasi 9 pintu risiko dalam 292 nanodetik. Namun, dokumen arsitektur belum merinci protokol komunikasi runtime antara kedua layanan (apakah menggunakan REST IPC lokal, PyO3 FFI, atau gRPC internal di Docker bridge).
- **Related Audit Finding IDs:** `AUDIT-FINDING-04`
- **Related Requirement/Rule IDs:** `ADR-006`, `NFR-PRF-01` (Evaluasi risiko sub-milidetik)
- **Existing Document References:**  
  - [ADR-006-hybrid-python-rust-architecture.md](file:///Users/nabilartanabil/SourceCode/AUTO-TRADE-AA/docs/02-architecture/adr/ADR-006-hybrid-python-rust-architecture.md)
  - [docker-compose.yml](file:///Users/nabilartanabil/SourceCode/AUTO-TRADE-AA/docker-compose.yml)
  - [engine/src/main.rs](file:///Users/nabilartanabil/SourceCode/AUTO-TRADE-AA/engine/src/main.rs)
- **Expected Deliverable:**  
  Dokumen spesifikasi teknis baru: `docs/02-architecture/RUST_ENGINE_INTEGRATION_SPEC.md`.
- **Scope:**  
  Format pertukaran data (JSON-RPC over IPC / HTTP micro-endpoint), fallback jika container Rust tidak tersedia, dan benchmarking latensi end-to-end.
- **Dependencies:** `DOC-TASK-002`.
- **Acceptance Criteria:**  
  1. Kontrak request dan response evaluasi risiko Rust terdokumentasi (skema input `SignalCandidate`, output `RiskEvaluationResult`).
  2. Mekanisme deployment di `docker-compose.yml` terpetakan jelas.
  3. Skenario fallback fail-closed (jika engine Rust tidak merespons dalam 10ms, order ditolak) didefinisikan.
- **Verification Method:**  
  Uji coba interkoneksi service container via curl/socket dan validasi skema JSON serde.
- **Assumptions or Unresolved Questions:**  
  Apakah protokol komunikasi yang dipilih untuk MVP adalah HTTP loopback lokal (`http://engine:8080`) atau shared memory / Unix socket?

---

### [P2 — MEDIUM]

#### DOC-TASK-005: Dokumentasi Metodologi Pengujian Backtesting & Klarifikasi Standar Profit Factor
- **Task ID:** `DOC-TASK-005`
- **Task Title:** Dokumentasi Metodologi Proxy Strategy pada Backtesting dan Kriteria Evaluasi Fase 6
- **Category:** `I. Testing Documentation` / `D. Requirements Clarification`
- **Priority:** `P2`
- **Status:** `DONE`
- **Completion Date:** 21 Oktober 2026
- **Description:**  
  Mendokumentasikan metodologi backtesting historis, alasan teknis penggunaan strategi proxy deterministik (EMA 20/50 + RSI) alih-alih pemanggilan LLM historis, serta merumuskan acceptance criteria yang realistis untuk kelulusan Fase 6.
- **Reason for the task:**  
  Dokumen `ROADMAP.md` Fase 6 mencatat temuan bahwa backtest 60 hari BTCUSDT menghasilkan Profit Factor 0.41 (di bawah target awal > 1.25) karena menggunakan strategi proxy deterministik. Hal ini belum terdokumentasi di `TESTING_PLAN.md`. Ketiadaan dokumentasi pemisahan antara "backtest strategi kuantitatif deterministik" vs "live paper trading dengan inferensi LLM Hermes" berpotensi menjadi penghambat (*blocker*) yang ambigu menuju evaluasi Fase 7.
- **Related Audit Finding IDs:** `AUDIT-FINDING-05`
- **Related Requirement/Rule IDs:** `AC-SIM-03`, Milestone 6 Acceptance Criteria
- **Existing Document References:**  
  - [TESTING_PLAN.md](file:///Users/nabilartanabil/SourceCode/AUTO-TRADE-AA/docs/01-requirements/TESTING_PLAN.md)
  - [ROADMAP.md](file:///Users/nabilartanabil/SourceCode/AUTO-TRADE-AA/docs/00-overview/ROADMAP.md#L126)
  - [backend/src/backtest/engine.py](file:///Users/nabilartanabil/SourceCode/AUTO-TRADE-AA/backend/src/backtest/engine.py)
- **Expected Deliverable:**  
  Pembaruan pada `docs/01-requirements/TESTING_PLAN.md` (Seksi Backtesting Methodology & Acceptance Thresholds).
- **Scope:**  
  Formula evaluasi Walk-Forward 70/30, simulasi slippage 0.05%, fee 0.10%, batasan biaya token LLM historis, dan kriteria transisi ke paper trading soak test.
- **Dependencies:** Tidak ada.
- **Acceptance Criteria:**  
  1. Rasional mengapa LLM tidak dipanggil per-candle historis dijelaskan secara finansial (biaya token).
  2. Formula matematis perhitungan Profit Factor, Net Expectancy, dan Max Drawdown diuraikan konsisten dengan `backend/src/backtest/engine.py`.
  3. Kriteria kelulusan formal Fase 6 diperjelas: pemisahan antara validasi fungsional engine backtest vs validasi performa live Hermes paper trading.
- **Verification Method:**  
  Review terhadap hasil eksekusi unit test `backend/src/backtest/test_backtest.py`.
- **Assumptions or Unresolved Questions:**  
  Berapa threshold minimal Profit Factor strategi proxy yang dianggap dapat diterima sebelum soak test live 30 hari diizinkan berjalan?

---

#### DOC-TASK-006: Dokumentasi Panduan Setup & Uji Operasional Bot Telegram Terotentikasi
- **Task ID:** `DOC-TASK-006`
- **Task Title:** Penyusunan Runbook Operasional Bot Telegram dan Verifikasi Pengendalian Darurat
- **Category:** `J. Operational Documentation` / `H. Security Documentation`
- **Priority:** `P2`
- **Status:** `DONE`
- **Completion Date:** 21 Oktober 2026
- **Description:**  
  Menyusun panduan langkah demi langkah pendaftaran bot Telegram melalui BotFather, konfigurasi `TELEGRAM_ALLOWED_USER_ID`, dan prosedur pengujian verifikasi perintah darurat (`/kill`).
- **Reason for the task:**  
  Modul bot Telegram telah selesai di-scaffold di `backend/src/control/telegram_bot.py`, namun belum ada petunjuk operasional di `docs/` yang membimbing operator tentang cara menemukan ID Telegram mereka, mengamankan token bot, atau memverifikasi bahwa pengguna yang tidak berwenang (*unauthorized users*) benar-benar di-drop secara silent.
- **Related Audit Finding IDs:** `AUDIT-FINDING-06`
- **Related Requirement/Rule IDs:** `AC-CTL-01`, `AC-CTL-02`, `RBAC-TG-01`
- **Existing Document References:**  
  - [RBAC_AND_TELEGRAM_ACCESS.md](file:///Users/nabilartanabil/SourceCode/AUTO-TRADE-AA/docs/05-security/RBAC_AND_TELEGRAM_ACCESS.md)
  - [backend/src/control/telegram_bot.py](file:///Users/nabilartanabil/SourceCode/AUTO-TRADE-AA/backend/src/control/telegram_bot.py)
- **Expected Deliverable:**  
  File baru `docs/05-security/TELEGRAM_BOT_SETUP_AND_RUNBOOK.md`.
- **Scope:**  
  Pendaftaran bot, konfigurasi `.env`, validasi allowlist, uji coba perintah `/status`, `/pause`, `/resume`, `/kill`, serta troubleshooting koneksi polling webhook.
- **Dependencies:** Tidak ada.
- **Acceptance Criteria:**  
  1. Instruksi memperoleh `TELEGRAM_BOT_TOKEN` dan `TELEGRAM_ALLOWED_USER_ID` terdokumentasi ringkas dan aman.
  2. Contoh payload interaksi perintah Telegram dicantumkan lengkap.
  3. Prosedur uji coba drill penolakan unauthorized ID terdokumentasi (AC-CTL-02).
- **Verification Method:**  
  Validasi alur kode pada `backend/src/control/telegram_bot.py`.
- **Assumptions or Unresolved Questions:** Tidak ada.

---

#### DOC-TASK-007: Matriks Penelusuran Kebutuhan ke Kode (Requirements-to-Code Traceability)
- **Task ID:** `DOC-TASK-007`
- **Task Title:** Penyusunan Matriks Keterlacakan Kebutuhan Bisnis ke Modul Implementasi Sumber Kode
- **Category:** `K. Documentation-to-Code Traceability`
- **Priority:** `P2`
- **Status:** `DONE`
- **Completion Date:** 21 Oktober 2026
- **Description:**  
  Menyusun matriks pemetaan yang menghubungkan setiap Kebutuhan Bisnis (`BR-xxx`), Kebutuhan Fungsional (`FR-xxx`), dan Kriteria Penerimaan (`AC-xxx`) ke file kode sumber Python/Rust/React dan unit test terkait.
- **Reason for the task:**  
  Repositori telah berkembang pesat dari Tahap 0 menjadi Fase 1–6 dengan puluhan file sumber baru. Tanpa matriks keterlacakan, auditor dan pengembang kesulitan memverifikasi kepatuhan kode terhadap spesifikasi arsitektur tanpa membaca seluruh basis kode.
- **Related Audit Finding IDs:** `AUDIT-FINDING-07`
- **Related Requirement/Rule IDs:** Seluruh `BR`, `FR`, `NFR`, dan `AC`
- **Existing Document References:**  
  - [BUSINESS_REQUIREMENTS.md](file:///Users/nabilartanabil/SourceCode/AUTO-TRADE-AA/docs/01-requirements/BUSINESS_REQUIREMENTS.md)
  - [FUNCTIONAL_REQUIREMENTS.md](file:///Users/nabilartanabil/SourceCode/AUTO-TRADE-AA/docs/01-requirements/FUNCTIONAL_REQUIREMENTS.md)
  - [ACCEPTANCE_CRITERIA.md](file:///Users/nabilartanabil/SourceCode/AUTO-TRADE-AA/docs/01-requirements/ACCEPTANCE_CRITERIA.md)
- **Expected Deliverable:**  
  Dokumen `docs/audit/REQUIREMENTS_TRACEABILITY_MATRIX.md`.
- **Scope:**  
  Pemetaan 100% item kebutuhan ke file backend, engine, frontend, dan unit test.
- **Dependencies:** `DOC-TASK-002`, `DOC-TASK-003`.
- **Acceptance Criteria:**  
  1. Setiap ID kebutuhan fungsional memiliki minimal satu path file implementasi dan satu path file test pengujian.
  2. Status pemenuhan kebutuhan (Fulfilled / Partial / Pending) dinyatakan secara faktual.
- **Verification Method:**  
  Audit tautan file dan verifikasi git tree repositori.
- **Assumptions or Unresolved Questions:** Tidak ada.

---

### [P3 — LOW]

#### DOC-TASK-008: Spesifikasi Desain UI/UX & State Reaktivitas Komponen Maskot Bull vs Bear
- **Task ID:** `DOC-TASK-008`
- **Task Title:** Dokumentasi Spesifikasi UI/UX Komponen Interaktif dan State Maskot Bull/Bear
- **Category:** `A. Missing Documentation` / `E. Business Process Documentation`
- **Priority:** `P3`
- **Status:** `DONE`
- **Completion Date:** 21 Oktober 2026
- **Description:**  
  Mendokumentasikan aturan bisnis visual, ambang batas status emosional maskot (Bull/Bear), palet warna glow PnL, dan struktur navigasi dashboard web Next.js 15.
- **Reason for the task:**  
  Enam commit terakhir menambahkan maskot SVG Bull/Bear, animasi glow PnL, count-up numbers, dan splash screen interaktif. Seluruh komponen ini berfungsi sangat baik di frontend, namun belum ada dokumen spesifikasi UI/UX yang mencatat aturan perubahan status visual maskot (misal: kapan Bull senang, kapan Bear menang, threshold persentase profit/loss untuk memicu glow).
- **Related Audit Finding IDs:** `AUDIT-FINDING-08`
- **Related Requirement/Rule IDs:** `FR-UI-01`, `FR-UI-02`
- **Existing Document References:**  
  - [frontend/src/components/ProfitLossMascot.tsx](file:///Users/nabilartanabil/SourceCode/AUTO-TRADE-AA/frontend/src/components/ProfitLossMascot.tsx)
  - [frontend/src/components/PnlGlow.tsx](file:///Users/nabilartanabil/SourceCode/AUTO-TRADE-AA/frontend/src/components/PnlGlow.tsx)
- **Expected Deliverable:**  
  Dokumen baru `docs/01-requirements/UI_UX_SPECIFICATION.md`.
- **Scope:**  
  State machine maskot visual, token warna Tailwind, transisi responsif mobile/desktop, dan integrasi data WebSocket ticker.
- **Dependencies:** Tidak ada.
- **Acceptance Criteria:**  
  1. Aturan matematis transisi ekspresi maskot (Profit > 0% vs Loss < 0%) terdokumentasi.
  2. Hirarki komponen halaman dashboard (`/`, `/risk`, `/wallets`) dipetakan jelas.
  3. Panduan styling dan aset vector SVG tercatat untuk referensi pemeliharaan tim.
- **Verification Method:**  
  Review terhadap source code `frontend/src/components/mascots/`.
- **Assumptions or Unresolved Questions:** Tidak ada.
