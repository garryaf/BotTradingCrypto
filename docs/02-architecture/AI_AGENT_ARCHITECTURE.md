# ARSITEKTUR MULTI-AGENT (AI AGENT ARCHITECTURE)
**Dokumen:** `docs/02-architecture/AI_AGENT_ARCHITECTURE.md`  
**Proyek:** AI Crypto Trading & Copy-Trading Platform (AUTO-TRADE-AA)  
**Versi:** 1.0.0 (Tahap 0)  
**Status:** Draf Resmi Arsitektur  

---

Dokumen ini mendefinisikan desain arsitektur sistem multi-agent bertenaga kecerdasan buatan dengan **Hermes Agent** sebagai orkestrator sentral dan agen-agen spesialis analitik.

---

## 0. Implementasi Aktual (diverifikasi audit 2026-10-26)

> Bagian 1–5 di bawah adalah **desain target**. Kode saat ini menjalankan versi yang lebih sederhana; tabel ini memetakan setiap peran ke kode yang benar-benar berjalan.

Hermes adalah **satu orchestrator** (`backend/src/agents/hermes.py`, `run_hermes_loop`, siklus 300 detik untuk BTCUSDT/ETHUSDT/SOLUSDT) yang menjalankan **tiga panggilan LLM berurutan**. Tiap panggilan memakai prompt dari `.agents/skills/<skill>/SKILL.md` dan outputnya wajib lolos skema Pydantic (`agents/schemas.py`); output yang gagal skema dicatat (`llm_requests.status_code = 422`) dan siklus untuk simbol itu dihentikan. Risiko dan eksekusi **bukan** agen LLM — keduanya kode deterministik.

| Peran | Implementasi aktual | Jenis | Menulis ke |
|---|---|---|---|
| Analisis pasar (Market Context) | skill `market-regime-detection` → `RegimeResult`; konteks EMA20/50 + RSI14 (`agents/indicators.py`) dari candle M1 | LLM + deterministik | `llm_requests` |
| Keamanan token | skill `token-and-contract-safety` → `SafetyResult`; konteks hanya aturan Binance Spot (status, spread, volume 24h) | LLM | `llm_requests` |
| Sintesis sinyal (Strategy Signal) | skill `signal-scoring-hybrid` → `SignalResult` (BUY/SELL/HOLD/NO_TRADE + level harga) | LLM | `llm_requests`, `trading_signals` (PENDING) |
| Trader profiling / discovery | Kandidat dimasukkan operator (`POST /api/v1/admin/wallets`); riwayat swap dikumpulkan `ingestion/solana.py`; `agents/wallet_scorer.py` (`run_wallet_scoring_loop`, 300 detik) mempromosikan skor ≥ 70 ke `PENDING_REVIEW`; operator menyetujui (`PATCH /api/v1/admin/wallets/{address}`) — rumus + keputusan manusia, bukan LLM | deterministik | `wallets` |
| Copy-trade | `agents/copy_trade.py`, dipicu `ingestion/solana.py` untuk swap **BUY** baru dari wallet `ACTIVE_MONITORED`; otoritas mint dibaca on-chain, harga & likuiditas dari DEXScreener. SELL tidak disalin | deterministik | `agent_runs`, `trading_signals` (PENDING), `market_snapshots` |
| Manajemen risiko | `risk/gate.py` (9 pintu + circuit breaker), opsional dikonfirmasi `engine/` (Rust) dengan ambang yang sama (dikirim di payload) | deterministik | `risk_checks` |
| Eksekusi | `risk/engine.py` + `risk/broker.py` — **paper broker saja** | deterministik | `paper_orders`, `paper_trades`, `positions`, `portfolio_snapshots` |

Selisih terhadap desain target:
- Skill `risk-gate-validation` dan `position-sizing-compounding` tidak dimuat runtime; aturannya diimplementasikan langsung di `risk/gate.py` dan `risk/sizing.py`.
- Belum ada: berita/sentimen sebagai sumber data, audit on-chain token SPL (mint/freeze authority, LP, holder), dan state graph. Alur Hermes linear dan tanpa resume; siklus yang gagal di tengah diulang dari awal pada siklus berikutnya.
- Satu `agent_runs` per siklus; ketiga panggilan LLM ditautkan lewat `llm_requests.agent_run_id`, dan sinyal lewat `trading_signals.agent_run_id`.

Batas otoritas di §4 berlaku penuh dan terverifikasi: agen hanya dapat membuat `trading_signals` berstatus PENDING. Order hanya dibuat Risk Engine setelah semua pintu lolos, maksimal satu verdict (dan satu order) per akun per sinyal.

---

## 1. Topologi Hermes Multi-Agent Workflow

```
                               ┌─────────────────────────────────┐
                               │   Hermes Workflow Orchestrator  │
                               │   (Task Dispatcher & State Graph)│
                               └───────────────┬─────────────────┘
                                               │
             ┌─────────────────────────────────┼─────────────────────────────────┐
             │                                 │                                 │
             ▼                                 ▼                                 ▼
┌─────────────────────────┐       ┌─────────────────────────┐       ┌─────────────────────────┐
│   Token Safety Agent    │       │   Market Context Agent  │       │ Trader Profiling Agent  │
│ (Audit Kontrak & Otoritas)│     │(Likuiditas, Volatilitas)│       │ (Evaluasi Metrik Wallet)│
└────────────┬────────────┘       └────────────┬────────────┘       └────────────┬────────────┘
             │                                 │                                 │
             └─────────────────────────────────┼─────────────────────────────────┘
                                               │
                                               ▼
                                  ┌─────────────────────────┐
                                  │  Strategy Signal Agent  │
                                  │(Sintesis Sinyal Trading)│
                                  └────────────┬────────────┘
                                               │ Sinyal Terstruktur JSON
                                               ▼
                                  ┌─────────────────────────┐
                                  │ Deterministic Risk Gate │
                                  │ (Non-bypassable Safety) │
                                  └─────────────────────────┘
```

---

## 2. Peran & Tanggung Jawab Hermes Orchestrator
Hermes Orchestrator bertindak sebagai koordinator alur kerja analitik yang beroperasi berdasarkan grafik status (*state graph*). Tugas utamanya:
1. Menerima event pemicu (misal swap baru terdeteksi atau jadwal pemindaian pasar berkala).
2. Menyiapkan konteks terisolasi dan menugaskan tugas ke agen spesialis terkait.
3. Mengumpulkan keluaran terstruktur dari agen-agen spesialis.
4. Memvalidasi bahwa setiap agen menghasilkan format data yang sah sebelum meneruskan konteks ke agen strategi.
5. Mencatat seluruh siklus hidup eksekusi (*agent run*) ke basis data untuk auditabilitas penuh.

---

## 3. Spesifikasi Agen-Agen Spesialis

### 3.1 Token Safety Agent
- **Fungsi:** Menilai integritas dan risiko penipuan teknis dari smart contract token SPL di Solana.
- **Input Konteks:**
  - Status `mint_authority` (apakah dev masih bisa mencetak token tak terbatas).
  - Status `freeze_authority` (apakah dev bisa membekukan saldo investor).
  - Persentase suplai token yang dikuasai oleh 10 wallet terbesar.
  - Status kolam likuiditas (apakah LP token di-burn atau dikunci).
- **Output Terstruktur (Pydantic Schema):**
  ```json
  {
    "token_mint": "string",
    "safety_score": 85,
    "risk_level": "LOW",
    "critical_flags": [],
    "mint_authority_revoked": true,
    "freeze_authority_revoked": true,
    "lp_burned_pct": 100.0,
    "top_10_holders_pct": 14.2,
    "summary_rationale": "Kontrak aman, otoritas minting & freeze dicabut penuh, likuiditas terkunci."
  }
  ```
- **Aturan Batas:** Jika `freeze_authority_revoked == false`, skor keamanan otomatis menjadi 0 dan `risk_level: CRITICAL`.

### 3.2 Market Context Agent
- **Fungsi:** Mengukur kondisi likuiditas, rasio volume terhadap likuiditas, serta volatilitas jangka pendek pasangan token.
- **Input Konteks:** Snapshot harga per menit (15-60 menit terakhir), kedalaman likuiditas pool AMM (USD), volume perdagangan 24 jam.
- **Output Terstruktur:**
  ```json
  {
    "token_mint": "string",
    "pool_liquidity_usd": 125000.0,
    "volume_24h_usd": 450000.0,
    "volatility_1h_pct": 3.4,
    "market_regime": "ACCUMULATION_LIQUID",
    "estimated_slippage_for_1_sol_pct": 0.42
  }
  ```

### 3.3 Trader Profiling / Discovery Agent
- **Fungsi:** Mengelompokkan gaya trading dan mengevaluasi kualitas performa dompet target yang ditemukan di on-chain.
- **Input Konteks:** Riwayat 50-100 transaksi terakhir wallet, nilai PnL bersih historis, frekuensi trading, rata-rata holding time.
- **Output Terstruktur:**
  ```json
  {
    "wallet_address": "string",
    "trader_category": "MOMENTUM_SWING",
    "calculated_score": 78.5,
    "net_pnl_sol": 42.8,
    "profit_factor": 2.45,
    "max_drawdown_pct": 12.3,
    "wash_trading_suspicion": "LOW",
    "recommendation": "APPROVE_FOR_MONITORING"
  }
  ```

### 3.4 Strategy Signal Agent
- **Fungsi:** Menyintesis temuan dari seluruh agen spesialis untuk merumuskan usulan sinyal perdagangan terstruktur.
- **Input Konteks:** Hasil evaluasi Token Safety, Market Context, dan detail transaksi copy-trade asal.
- **Output Terstruktur:**
  ```json
  {
    "signal_id": "sig-sol-20261014-001",
    "strategy_id": "copy_trade_mirror_v1",
    "token_mint": "DezXAZ8z7PnrnRJjz3wXBoRgixCa6xjnB7YaB1pPB263",
    "action": "BUY",
    "target_price_sol": 0.000000835,
    "recommended_allocation_pct": 0.05,
    "confidence_score": 0.88,
    "rationale": "Wallet target mengakumulasi posisi dengan konfirmasi likuiditas pool stabil dan kontrak aman."
  }
  ```

---

## 4. Pembatasan Hak Akses & Batas Otoritas Agen (Least Privilege)

1. **Zero Direct Execution Authority:** Tidak ada satu pun agen AI yang diberikan fungsi eksekusi order (*order execution tool*), fungsi penulisan saldo, atau izin koneksi langsung ke antarmuka trading live.
2. **Ketiadaan Akses Kredensial:** Agen AI beroperasi murni melalui pertukaran teks dan JSON. Agen tidak memiliki akses ke environment variables atau file konfigurasi rahasia.
3. **Validasi Skema Wajib:** Setiap respons teks yang dihasilkan LLM wajib lolos validasi skema Pydantic sebelum diizinkan mengalir ke langkah pemrosesan berikutnya. Respons dengan format cacat otomatis ditolak.

---

## 5. Sistem Keahlian Dinamis Agen (Dynamic AI Agent Skill System)

Untuk menghemat konsumsi token LLM hingga 70% dan meningkatkan akurasi penalaran, sistem menerapkan arsitektur **Dynamic Skill Loading**:

```
                              [ Hermes Orchestrator ]
                                         │
                         ┌───────────────┴───────────────┐
                         │ Menentukan Kebutuhan Tugas    │
                         ▼                               ▼
               [ Tugas: Deteksi Rezim ]       [ Tugas: Sizing & Compounding ]
                         │                               │
                         ▼ (Muat Hanya 1 Skill)          ▼ (Muat Hanya 1 Skill)
                 .agents/skills/                 .agents/skills/
             market-regime-detection/        position-sizing-compounding/
                    SKILL.md                        SKILL.md
                         │                               │
                         └───────────────┬───────────────┘
                                         │ Injeksi Ringkas ke Prompt
                                         ▼
                             [ AI Model Gateway ]
                        (OpenRouter / 9Route / LLM)
```

### 5.1 Katalog Skill yang Tersedia (`.agents/skills/`)
1. **`market-regime-detection`:** Berisi formula klasifikasi rezim Trending Bullish, Trending Bearish, Sideways, dan Volatile High-Risk berbasis EMA 20/50/200, RSI, MACD, ATR, VWAP, dan ADX.
2. **`signal-scoring-hybrid`:** Berisi logika sintesis 3 pilar (Trend Following, Momentum Breakout, Mean Reversion), rumus Confidence Score, dan 4 filter eliminasi sinyal palsu.
3. **`risk-gate-validation`:** Standar validasi 9 pintu risiko deterministik (Risk 0.5%, Daily Loss 2%, Drawdown 8%, Expectancy Positif, Cek Spread).
4. **`position-sizing-compounding`:** Formula matematis lot sizing berdasarkan risiko 0.5% ekuitas, compounding adaptif, level TP1 (50% partial), TP2, dan trailing stop ATR.
5. **`token-and-contract-safety`:** Prosedur audit on-chain token SPL Solana (freeze/mint authority, LP burn status) dan validasi precision Binance Spot.

### 5.2 Keuntungan Penghematan & Agilitas
- **Efisiensi Token:** System prompt dasar tetap ramping (~200 token). Skill spesifik hanya disuntikkan secara dinamis saat agen mengeksekusi sub-task relevan (~400 token), bukan memuat seluruh aturan ensiklopedia trading (~5.000 token) setiap saat.
- **Bebas Agnostik Model AI:** Skill ditulis dalam format Markdown standar yang dapat dibaca dan dieksekusi dengan baik oleh model apa pun (Claude, Llama, Gemini, DeepSeek, GPT).
- **Ekstensibilitas Mandiri:** Pengembang atau agen dapat memperbarui atau menambah skill baru di direktori `.agents/skills/<nama-skill>/SKILL.md` tanpa perlu mengubah kode sumber inti aplikasi.
