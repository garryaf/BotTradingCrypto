# SPESIFIKASI INTEGRASI RUST ENGINE
**Dokumen:** `docs/02-architecture/RUST_ENGINE_INTEGRATION_SPEC.md`  
**Proyek:** AI Crypto Trading & Copy-Trading Platform (AUTO-TRADE-AA)  
**Versi:** 1.0.0 (MVP — Fase 2)  
**Status:** Draf Resmi Arsitektur  
**Referensi:** [ADR-006](./adr/ADR-006-hybrid-python-rust-architecture.md)  

---

## 1. Ringkasan

Dokumen ini merinci batas tanggung jawab (*responsibility boundary*), protokol komunikasi runtime, kontrak skema data, dan perilaku fallback antara:

- **Python FastAPI** (`backend/`) — AI Orchestration & REST API Layer
- **Rust Core Engine** (`engine/`) — High-Speed Risk Gate & Market Data Ingestion

Spesifikasi ini mengimplementasikan keputusan ADR-006 dan memenuhi `NFR-PRF-01` (evaluasi risiko sub-milidetik, target ≤ 300ns internal, ≤ 10ms end-to-end termasuk IPC).

---

## 2. Batas Tanggung Jawab

### 2.1 Rust Engine (`engine/`)

| Tanggung Jawab | Detail |
|---|---|
| **Evaluasi Risk Gate** | Mengevaluasi 9 pintu risiko deterministik terhadap `SignalCandidate`. Benchmark internal: **292ns** per evaluasi. |
| **Market Data Ingestion** | Koneksi WebSocket Binance Spot (L1 ticker, L2 orderbook). Parser instruksi on-chain Solana (`solana-sdk`). |
| **OHLCV Aggregation** | Mengagregasi tick price menjadi candle OHLCV dan menulis ke tabel `market_ohlcv` via koneksi PostgreSQL langsung. |
| **Dead Letter Queue** | Menulis event gagal ke tabel `ingestion_errors` (DLQ). |
| **Paper Matching Engine** | Simulasi fill order dengan model slippage matematis dan in-memory ledger. |

### 2.2 Python FastAPI (`backend/`)

| Tanggung Jawab | Detail |
|---|---|
| **AI Agent Orchestration** | Menjalankan Hermes Multi-Agent Framework dan memanggil LLM Gateway (OpenRouter/9Route). |
| **Signal Generation** | Menghasilkan `SignalCandidate` dari output agen AI. |
| **Risk Gate Client** | Mengirim `SignalCandidate` ke Rust engine dan menunggu `RiskEvaluationResult`. |
| **REST API & Telegram Bot** | Menyediakan endpoint kontrol dan notifikasi operator. |
| **Alembic Migrations** | Mengelola skema database PostgreSQL. |

---

## 3. Protokol Komunikasi (IPC)

### 3.1 Pilihan Protokol: HTTP Loopback Lokal

Untuk MVP, protokol yang dipilih adalah **HTTP/1.1 JSON over Docker internal network** (`http://engine:8080`).

**Alasan pemilihan:**
- Zero konfigurasi tambahan pada Docker Compose (bridge network sudah tersedia).
- Mudah di-curl untuk debugging manual tanpa tooling khusus.
- Overhead serialisasi JSON dapat diterima untuk target latensi 10ms end-to-end.

```
shortcut: HTTP JSON IPC, bukan Unix socket/gRPC; upgrade ke Unix socket jika latensi > 5ms konsisten dalam soak test 30 hari.
```

**Topologi deployment (`docker-compose.yml`):**

```
[backend:8000] ──HTTP POST /evaluate──> [engine:8080]
      |                                       |
      |<──────── RiskEvaluationResult ────────|
      |
[postgres:5432] <── (kedua service menulis langsung)
```

> **Catatan:** Rust engine service belum ditambahkan ke `docker-compose.yml` per status Fase 2. Lihat Seksi 6.

### 3.2 Endpoint Risk Gate

**Request:**
```
POST http://engine:8080/evaluate
Content-Type: application/json
```

**Response:**
```
200 OK
Content-Type: application/json
```

---

## 4. Kontrak Skema Data

### 4.1 Request: `SignalCandidate`

Payload dikirim dari Python FastAPI ke Rust engine untuk evaluasi:

```json
{
  "signal_id": "33eebc99-9c0b-4ef8-bb6d-6bb9bd380a11",
  "symbol": "SOLUSDT",
  "action": "BUY",
  "target_entry_price": 152.40,
  "suggested_stop_loss": 149.35,
  "suggested_take_profit_1": 156.98,
  "suggested_take_profit_2": 161.55,
  "recommended_allocation_pct": 0.005,
  "confidence_score": 0.84,
  "snapshot": {
    "price_usd": 152.40,
    "bid_price": 152.38,
    "ask_price": 152.42,
    "spread_pct": 0.0262,
    "snapshot_age_seconds": 4,
    "pool_liquidity_usd": 1250000.00
  },
  "portfolio": {
    "total_equity_usd": 10245.32,
    "cash_balance_usd": 7685.12,
    "daily_realized_pnl_usd": 125.40,
    "daily_loss_pct": 0.45,
    "high_water_mark_usd": 10450.00,
    "current_drawdown_pct": 1.96,
    "open_positions_count": 1,
    "net_expectancy_usd": 12.45
  }
}
```

| Field | Tipe | Deskripsi |
|---|---|---|
| `signal_id` | `UUID string` | ID sinyal dari tabel `trading_signals`. |
| `snapshot.snapshot_age_seconds` | `int` | Usia data snapshot; Gate 9 gagal jika ≥ 30. |
| `portfolio.open_positions_count` | `int` | Jumlah posisi terbuka; Gate 8b gagal jika ≥ `MAX_OPEN_POSITIONS`. |
| `portfolio.daily_loss_pct` | `float` | Persentase kerugian hari ini; Gate 3 gagal jika ≥ 2.0. |
| `portfolio.current_drawdown_pct` | `float` | Drawdown dari HWM; Gate 4 gagal jika ≥ 8.0. |

### 4.2 Response: `RiskEvaluationResult`

```json
{
  "signal_id": "33eebc99-9c0b-4ef8-bb6d-6bb9bd380a11",
  "passed": true,
  "gates": {
    "expectancy_check": true,
    "risk_per_trade_check": true,
    "daily_loss_check": true,
    "drawdown_check": true,
    "spread_check": true,
    "stop_loss_check": true,
    "balance_lot_check": true,
    "circuit_breaker_check": true,
    "max_positions_check": true,
    "data_freshness_check": true
  },
  "rejection_reasons": [],
  "evaluation_ns": 292
}
```

| Field | Tipe | Deskripsi |
|---|---|---|
| `passed` | `bool` | `true` hanya jika **semua** 10 gate bernilai `true`. |
| `gates` | `object` | Hasil evaluasi per gate (cocok 1:1 dengan kolom tabel `risk_checks`). |
| `rejection_reasons` | `string[]` | Daftar kode gate yang gagal, misal: `["DAILY_LOSS_EXCEEDED", "SPREAD_TOO_HIGH"]`. |
| `evaluation_ns` | `int` | Durasi evaluasi internal Rust dalam nanodetik (monitoring). |

---

## 5. Perilaku Fallback (Fail-Closed)

> **Aturan Keselamatan:** Jika Rust engine tidak merespons atau mengembalikan error, sistem Python **WAJIB menolak sinyal (fail-closed)**. Order tidak boleh dieksekusi tanpa konfirmasi evaluasi risiko yang valid.

| Kondisi | Perilaku Python |
|---|---|
| HTTP timeout > **10ms** | Tolak sinyal. Catat `rejection_reasons: ["ENGINE_TIMEOUT"]`. |
| HTTP error 5xx dari engine | Tolak sinyal. Catat `rejection_reasons: ["ENGINE_ERROR"]`. |
| Engine container tidak tersedia (`ConnectionRefused`) | Tolak sinyal. Set circuit breaker `FROZEN`. Kirim notifikasi Telegram `CRITICAL`. |
| Response JSON tidak valid / skema salah | Tolak sinyal. Catat `rejection_reasons: ["ENGINE_INVALID_RESPONSE"]`. |
| `passed == false` dari engine | Tolak sinyal. Simpan `rejection_reasons` ke tabel `risk_checks`. |

**Kode Python pseudocode (referensi implementasi):**

```python
# shortcut: timeout 10ms hardcoded, jadikan konfigurasi via user_settings jika perlu tuning
async def call_risk_engine(candidate: SignalCandidate) -> RiskEvaluationResult:
    try:
        resp = await httpx.post(
            f"{settings.ENGINE_URL}/evaluate",
            json=candidate.model_dump(),
            timeout=0.010,  # 10ms
        )
        resp.raise_for_status()
        return RiskEvaluationResult.model_validate(resp.json())
    except Exception:
        return RiskEvaluationResult(passed=False, rejection_reasons=["ENGINE_TIMEOUT"])
```

---

## 6. Konfigurasi Deployment

### 6.1 Environment Variables

| Variabel | Default | Deskripsi |
|---|---|---|
| `ENGINE_URL` | `http://engine:8080` | Base URL Rust engine di Docker network. |
| `ENGINE_TIMEOUT_MS` | `10` | Timeout request IPC dalam milidetik. |
| `MAX_OPEN_POSITIONS` | `3` | Batas maksimal posisi terbuka (Gate 8b). |

### 6.2 Penambahan `docker-compose.yml` (Belum Diimplementasikan)

Rust engine service perlu ditambahkan ke `docker-compose.yml`:

```yaml
# Tambahkan ke docker-compose.yml saat engine siap dideploy:
  engine:
    build:
      context: ./engine
      dockerfile: Dockerfile  # multi-stage: cargo build --release
    environment:
      DATABASE_URL: ${DATABASE_URL}
    ports:
      - "8080:8080"  # hanya expose ke internal network, bukan host
    depends_on:
      postgres:
        condition: service_healthy
```

> **Status:** Engine service belum ada di `docker-compose.yml` (hanya `postgres` dan `backend`). Ditambahkan saat Fase 3 engine Rust aktif di-deploy.

---

## 7. Benchmarking & Monitoring

| Metrik | Target | Cara Ukur |
|---|---|---|
| Latensi internal Rust (Risk Gate) | ≤ 300ns | Field `evaluation_ns` di response |
| Latensi end-to-end Python → Rust → Python | ≤ 10ms | Timestamp Python sebelum/sesudah `call_risk_engine()` |
| Error rate engine | < 0.1% | Count `ENGINE_TIMEOUT` + `ENGINE_ERROR` di `risk_checks` |

Log `evaluation_ns` dicatat ke tabel `risk_checks` (kolom `evaluated_at` sudah ada; tambahkan kolom `engine_latency_ms` jika monitoring diperlukan lebih detail).

---

## 8. Item yang Dilewati / Risiko

- **FFI (PyO3)**: Opsi integrasi in-process PyO3 dilewati untuk MVP karena menambah kompleksitas build. Upgrade jika HTTP IPC menunjukkan latensi > 5ms konsisten.
- **gRPC**: Dilewati karena membutuhkan protobuf toolchain tambahan. Pertimbangkan jika jumlah sinyal per detik > 100.
- **Cargo.toml / src/**: Belum ada kode Rust di `engine/` selain `Cargo.lock`. Spesifikasi ini mendokumentasikan kontrak yang harus diimplementasikan.
- **Risiko**: Tanpa engine aktif, `docker-compose.yml` belum menyertakan service `engine`. Semua request akan timeout dan fail-closed sampai engine di-deploy.
