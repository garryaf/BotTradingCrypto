# RENCANA PENGUJIAN KOMPREHENSIF (COMPREHENSIVE TESTING PLAN)
**Dokumen:** `docs/01-requirements/TESTING_PLAN.md`  
**Proyek:** AI Crypto Trading & Copy-Trading Platform (AUTO-TRADE-AA)  
**Versi:** 1.1.0 (Fase 6 — Backtesting)  
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
  - **Rust Engine Gagal (IPC fail-closed):** `backend/src/risk/test_engine_client.py` (jalankan `python -m src.risk.test_engine_client`) memakai `httpx.MockTransport` — hanya di test, bukan di runtime — untuk 10 skenario: lolos, ditolak engine, timeout, koneksi ditolak, HTTP 5xx, bukan JSON, skema salah, `passed=true` dengan gate gagal, `passed=true` tanpa gate, verdict untuk `signal_id` lain. Semua kegagalan wajib menghasilkan `passed=False`.

### 2.4 Simulation & Accounting Testing (Paper Broker Verification)
- **Fokus:** Memverifikasi bahwa simulator eksekusi mencerminkan kondisi pasar riil dan tidak mengalami distorsi akuntansi.
- **Skenario Pengujian:**
  - **Persamaan Akuntansi:** Setelah 100 transaksi virtual acak:
    $$\text{Cash Balance} + \sum (\text{Unrealized Value}) = \text{Total Equity}$$
    Deviasi pembukuan wajib $0.00$.
  - **Slippage & Fee Realism:** Memastikan harga fill paper order memperhitungkan taker fee (0.10% Binance / priority fee Solana) dan slippage minimal 0.05%.
  - **Pencegahan Look-Ahead Bias:** Memverifikasi bahwa mesin backtesting hanya membaca data dengan timestamp $\le t_{\text{simulasi}}$.

### 2.5 Drill Pengujian Darurat (Kill Switch Drill)
Mengacu pada spesifikasi [LIVE_TRADING_SAFETY_GATE.md](../../docs/05-security/LIVE_TRADING_SAFETY_GATE.md) Kriteria 3:
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
| **Rust Engine IPC** | Spec §5 (fail-closed) | 10 skenario mock transport (timeout, 5xx, koneksi ditolak, JSON/skema invalid, verdict tak konsisten) | plain-assert `python -m src.risk.test_engine_client` | 100% kegagalan → `passed=False` |
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
   Semua panggilan ke Solana RPC (Helius) dan Binance API di-mock pada unit/integration test menggunakan `pytest-mock` atau `respx` untuk mencegah konsumsi kuota rate limit eksternal.
3. **Execution Command:**
   ```bash
   # Menjalankan seluruh test suite dengan laporan coverage
   pytest tests/ --cov=backend/src --cov-report=term-missing --cov-fail-under=85
   ```

---

## 5. Metodologi Backtesting Historis (Fase 6)

### 5.1 Konteks & Batasan

Sistem AUTO-TRADE-AA menggunakan AI agent Hermes (LLM) untuk menghasilkan sinyal trading di lingkungan live. Pemanggilan LLM **tidak dilakukan** pada setiap bar historis saat backtesting karena dua alasan:

1. **Biaya token**: Replay 60 hari data 1 menit BTCUSDT menghasilkan ~86.400 bar. Memanggil LLM per bar akan menelan biaya token yang tidak proporsional.
2. **Reproduksibilitas**: Respons LLM bersifat non-deterministik (sampling temperature > 0), sehingga tidak menghasilkan hasil yang dapat di-reproduce secara konsisten untuk validasi kuantitatif.

**Solusi:** Engine backtest (`backend/src/backtest/engine.py`) menggunakan **strategi proxy deterministik** yang merepresentasikan **pillar Trend Following** dari Hermes. Ini cukup untuk memvalidasi kebenaran Risk Gate, Paper Broker, dan akuntansi portofolio secara end-to-end — bukan untuk mengklaim performa historis AI.

### 5.2 Strategi Proxy Deterministik

**Implementasi:** [`backend/src/backtest/strategy.py`](../../backend/src/backtest/strategy.py)

| Parameter | Nilai | Sumber |
|---|---|---|
| Indikator Entry | EMA(20) > EMA(50) **dan** 50 ≤ RSI(14) ≤ 70 | `strategy.py:20-22` |
| Stop Loss | Entry × (1 − 2%) | `SL_PCT = 0.02` |
| Take Profit 1 (TP1) | Entry + 1.5 × Risk Unit | `TP1_R = 1.5` |
| Take Profit 2 (TP2) | Entry + 3.0 × Risk Unit | `TP2_R = 3.0` |
| Win Rate Prior | 55% (konservatif, bukan hasil fitting) | `estimated_winrate_pct = 55.0` |
| Min bars warmup | 51 bar (agar EMA50 valid) | `strategy.py:18` |

Strategi ini **hanya** merepresentasikan Trend Following — bukan Momentum Breakout atau Mean Reversion dari Hermes. Ini adalah *lower bound* validasi engine, bukan proyeksi performa live.

### 5.3 Metodologi Walk-Forward 70/30

**Implementasi:** [`backend/src/backtest/engine.py:43`](../../backend/src/backtest/engine.py#L43)

```python
split_idx = int(len(bars) * 0.7)  # 70% in-sample / 30% out-of-sample, chronological
```

| Segmen | Proporsi | Tujuan |
|---|---|---|
| **In-Sample** | 70% bar pertama (kronologis) | Observasi perilaku strategi proxy pada data training |
| **Out-of-Sample** | 30% bar terakhir (kronologis) | Validasi tanpa look-ahead bias pada data tak terlihat |

> **Penting:** Pembagian dilakukan **secara kronologis**, bukan acak. Tidak ada data masa depan yang bocor ke segmen in-sample (AC-SIM-03).

### 5.4 Simulasi Fee & Slippage

Backtest engine menggunakan fungsi produksi yang sama (`fee_for_venue`, `simulate_fills`) agar hasil mencerminkan kondisi nyata:

| Komponen | Nilai | Referensi |
|---|---|---|
| Taker Fee Binance Spot | **0.10%** dari notional | `BINANCE_TAKER_FEE_PCT` di `risk/gate.py` |
| Slippage simulasi | Dihitung dari `simulate_fills()` berbasis bid/ask | `risk/broker.py` |
| Data stale check | **Dinonaktifkan** (`is_stale=False`) — tidak relevan untuk replay historis | `engine.py:115`, docstring modul |

### 5.5 Formula Metrik Evaluasi

Implementasi aktual di fungsi `_metrics()` (`engine.py:26-38`):

$$\text{Profit Factor} = \frac{\sum \text{Wins}}{\sum |\text{Losses}|}$$

$$\text{Win Rate} = \frac{\text{Jumlah Trade Profit}}{\text{Total Trade}} \times 100\%$$

$$\text{Net PnL (USD)} = \sum_{\text{semua trade}} \text{PnL}_i$$

$$\text{Max Drawdown} = \max_t \left(\frac{\text{HWM}_t - \text{Equity}_t}{\text{HWM}_t}\right) \times 100\%$$

> **Catatan:** `profit_factor = inf` jika tidak ada loss sama sekali (gross_loss = 0), sesuai implementasi kode.

### 5.6 Pencegahan Look-Ahead Bias (AC-SIM-03)

Dari `engine.py:89`:
```python
signal = generate_signal(closes[:i + 1])  # AC-SIM-03: strictly no future bars
```

`generate_signal()` menerima **hanya** harga penutupan hingga bar `i` (inklusif). Bar `i+1` dan seterusnya tidak pernah diteruskan. Ini adalah implementasi pemenuhan AC-SIM-03.

### 5.7 Kriteria Kelulusan Fase 6

#### Kriteria Wajib (Fungsional Engine)
Backtest engine dinyatakan **lulus fungsional** jika:

| # | Kriteria | Target |
|---|---|---|
| F-1 | Tidak ada look-ahead bias (AC-SIM-03) | Terverifikasi dari struktur `closes[:i+1]` |
| F-2 | Akuntansi portofolio seimbang: `final_equity = cash + mark_to_market` | Deviasi = $0.00 |
| F-3 | Risk Gate deterministik dipatuhi (9 pintu diterapkan per sinyal) | 100% penerapan |
| F-4 | Fee dan slippage teraplikasi pada setiap fill | Tidak ada trade gratis |
| F-5 | Circuit breaker drawdown ≥ 8% membekukan entry baru | Diverifikasi per skenario |

#### Kriteria Transisi ke Soak Test (Paper Trading Live 30 Hari)
Sebelum Fase 7 (Paper Soak Test), backtesting **proxy** harus memenuhi:

| # | Metrik | Threshold Minimum | Catatan |
|---|---|---|---|
| P-1 | Profit Factor (out-of-sample) | **> 0** (ekspektasi positif) | Strategi proxy **bukan** cerminan AI live. Threshold > 1.0 untuk proxy bisa tidak realistis. |
| P-2 | Max Drawdown | **< 20%** | Jika melebihi, review parameter SL/TP proxy. |
| P-3 | Total trade (out-of-sample) | **≥ 10** | Sampel statistik minimum untuk evaluasi bermakna. |
| P-4 | Net Expectancy | **> 0 USD** | Pastikan fee tidak menghabiskan semua profit bruto. |

> **Pemisahan penting:** Kelulusan kriteria P-1 s.d. P-4 **hanya memvalidasi engine backtest bekerja benar**, bukan memproyeksikan performa live Hermes. Validasi performa AI Hermes dilakukan melalui **Soak Test Paper Trading 30 hari** (Fase 7), bukan melalui backtesting proxy.

