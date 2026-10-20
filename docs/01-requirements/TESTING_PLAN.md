# RENCANA PENGUJIAN KOMPREHENSIF (COMPREHENSIVE TESTING PLAN)
**Dokumen:** `docs/01-requirements/TESTING_PLAN.md`  
**Proyek:** AI Crypto Trading & Copy-Trading Platform (AUTO-TRADE-AA)  
**Versi:** 1.0.0 (Tahap 0)  
**Status:** Draf Resmi Rencana Pengujian  

---

## 1. Tujuan & Strategi Pengujian

Dokumen ini mendefinisikan strategi verifikasi kualitas, pengujian otomatis, dan pengujian ketahanan (*resilience*) untuk memastikan sistem beroperasi dengan prinsip **Safety-by-Design** dan **Fail-Closed**.

Setiap perubahan kode (*pull request*) wajib memenuhi piramida pengujian berikut:

```
        ▲
       / \
      /   \     E2E / Soak Test (30 Hari Paper Trading)
     /     \    ────────────────────────────────────────
    /       \   Integrasi & Contract Test (FastAPI, Alembic, DB)
   /         \  ────────────────────────────────────────────────
  /           \ Unit Test & Deterministik Risk Gate (Pytest, Mock)
 /─────────────\────────────────────────────────────────────────────
```

---

## 2. Taksonomi & Tingkatan Pengujian

### 2.1 Unit Testing (Pengujian Unit)
- **Fokus:** Menguji fungsi-fungsi murni, kalkulasi matematis, dan validasi skema tanpa ketergantungan jaringan eksternal.
- **Komponen Utama yang Diuji:**
  - **Deduplikasi Signature:** Memastikan algoritma hash set menolak transaksi duplikat.
  - **Indikator Teknikal:** Memvalidasi akurasi perhitungan EMA, RSI, MACD, ATR, dan VWAP terhadap baseline dataset benchmark.
  - **Skor Sinyal Hibrida:** Memverifikasi pembobotan sinyal Trend Following, Breakout, dan Mean Reversion.
  - **Kalkulasi Position Sizing:** Memverifikasi formula $\text{Lot} = (\text{Equity} \times 0.005) / |\text{Entry} - \text{SL}|$.
  - **Deterministic Risk Gate (9 Pintu):** Setiap pintu memiliki test case positif (lulus) dan negatif (ditolak dengan kode error spesifik).
- **Target Cakupan:** $\ge 90\%$ line coverage pada modul `risk_engine/`, `accounting/`, dan `safety_gate/`.

### 2.2 Integration Testing (Pengujian Integrasi)
- **Fokus:** Menguji interaksi antara modul backend dengan basis data PostgreSQL dan antarmuka model eksternal (menggunakan *mock*).
- **Komponen Utama yang Diuji:**
  - **Migrasi Database:** Siklus `upgrade()` dan `downgrade()` Alembic untuk memastikan integritas skema dan *foreign keys*.
  - **Integritas Transaksi ACID:** Menjalankan operasi pembaruan saldo virtual dan pembukaan posisi dalam satu blok transaksi database; kegagalan salah satu operasi wajib melakukan *rollback* penuh.
  - **AI Model Gateway Fallback:** Mensimulasikan respons HTTP 429 atau 500 dari OpenRouter dan memverifikasi pengalihan instan ke 9Route dalam waktu $\le 2.0$ detik.
  - **REST API Endpoints:** Menguji kontrak request/response pada endpoint `/api/v1/signals`, `/api/v1/positions`, dan `/api/v1/portfolio`.

### 2.3 Fail-Closed & Chaos Testing (Ketahanan Kegagalan)
- **Fokus:** Memastikan sistem bereaksi dengan menolak perdagangan (*fail-closed*) saat infrastruktur eksternal mengalami gangguan.
- **Skenario Pengujian:**
  - **Stale Price Feed:** Menginjeksikan snapshot data pasar berumur > 30 detik. Sistem wajib menolak sinyal dan mencatat log `DATA_STALE`.
  - **RPC Quota Exhaustion:** Mensimulasikan kuota RPC habis (HTTP 429 berulang). Ingestion pipeline wajib menerapkan *exponential backoff* dan beralih ke status jeda (*paused*).
  - **LLM Prompt Injection & Output Cacat:** Mengirimkan nama token berbahaya atau respons LLM tanpa format JSON valid. Parser Pydantic wajib menolak respons tanpa mengeksekusi order.
  - **Disconnect Network:** Memutus koneksi internet selama 60 detik; sistem tidak boleh mengalami crash atau corrupt data.

### 2.4 Simulation & Accounting Testing (Paper Broker Verification)
- **Fokus:** Memverifikasi bahwa simulator eksekusi mencerminkan kondisi pasar riil dan tidak mengalami distorsi akuntansi.
- **Skenario Pengujian:**
  - **Persamaan Akuntansi:** Setelah 100 transaksi virtual acak:
    $$\text{Cash Balance} + \sum (\text{Unrealized Value}) = \text{Total Equity}$$
    Deviasi pembukuan wajib $0.00$.
  - **Slippage & Fee Realism:** Memastikan harga fill paper order memperhitungkan taker fee (0.10% Bybit / priority fee Solana) dan slippage minimal 0.05%.
  - **Pencegahan Look-Ahead Bias:** Memverifikasi bahwa mesin backtesting hanya membaca data dengan timestamp $\le t_{\text{simulasi}}$.

### 2.5 Drill Pengujian Darurat (Kill Switch Drill)
Mengacu pada spesifikasi [LIVE_TRADING_SAFETY_GATE.md](file:///Users/nabilartanabil/SourceCode/AUTO-TRADE-AA/docs/05-security/LIVE_TRADING_SAFETY_GATE.md) Kriteria 3:
- **Prosedur Pengujian:**
  1. Sistem menjalankan aliran pengiriman sinyal buatan secara kontinu (10 sinyal/detik).
  2. Pemicu darurat diaktifkan (via perintah Telegram `/kill` atau tombol web).
  3. Catat timestamp aktivasi ($T_0$) dan timestamp order baru ditolak ($T_1$).
  4. Durasi reaksi $\Delta T = T_1 - T_0$.
- **Kriteria Lulus (Pass):** $\Delta T \le 2.0$ detik dilakukan sebanyak **5 kali pengujian berturut-turut** tanpa kegagalan.

---

## 3. Matriks Kriteria Penerimaan & Pengujian

| Kategori | ID Kriteria | Metode Pengujian | Alat / Framework | Target Lulus |
|---|---|---|---|---|
| **Ingestion** | AC-ING-01 s.d. AC-ING-04 | Mock stream 100 signature, inject stale data, mock HTTP 429 | `pytest`, `respx` | 100% dedup, 0 unhandled exceptions |
| **AI Gateway** | AC-AI-01 s.d. AC-AI-04 | Fuzzing schema JSON, inject HTTP 500 fallback, prompt injection test | `pytest`, `pydantic` | 100% valid schema, fallback < 2.0s |
| **Risk Gate** | AC-RSK-01 s.d. AC-RSK-05 | Uji batas 9 pintu serial, feed melanggar daily loss 2% & drawdown 8% | `pytest` | 100% penolakan deterministik |
| **Accounting** | AC-SIM-01 s.d. AC-SIM-03 | 50 cycle order acak, verifikasi high-water mark & deviasi | `pytest` | Deviasi akuntansi = 0.00 |
| **Telegram** | AC-CTL-01 s.d. AC-CTL-03 | Inject unauthorized user ID, pemicu `/kill` beruntun 5x | `pytest-asyncio` | Respon $\le 2.0$s, unauthorized 100% drop |
| **DevSecOps** | AC-OPS-01 s.d. AC-OPS-03 | Stress test container 2 jam di M1 Pro, regex scan secrets | Docker stats, `trufflehog` / regex | RAM $\le 8.0$ GB, 0 secrets bocor |

---

## 4. Konfigurasi Lingkungan Pengujian Lokal

1. **Database Uji Terisolasi:**
   Pengujian integrasi menggunakan container PostgreSQL khusus pengujian atau schema terisolasi (`test_auto_trade`) agar tidak mengotori data development:
   ```bash
   DATABASE_URL="postgresql+asyncpg://test_user:test_pass@localhost:5432/test_auto_trade" pytest tests/
   ```
2. **Mocking External Services:**
   Semua panggilan ke Solana RPC (Helius) dan Bybit API di-mock pada unit/integration test menggunakan `pytest-mock` atau `respx` untuk mencegah konsumsi kuota rate limit eksternal.
3. **Execution Command:**
   ```bash
   # Menjalankan seluruh test suite dengan laporan coverage
   pytest tests/ --cov=backend/src --cov-report=term-missing --cov-fail-under=85
   ```
