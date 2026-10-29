# 11 — Self-Check & Rust Test Run (P0-1 / GAP-13)

**Tanggal:** 2026-10-26
**Lingkup:** menjalankan seluruh self-check backend (README Step 5) + `cargo test` engine Rust. READ-ONLY terhadap sumber; tidak ada order live, tidak ada operasi DB destruktif. Tidak ada Postgres yang dibutuhkan (self-check bersifat pure/plain-assert, tanpa DB/API key).

## Lingkungan
- Docker: RUNNING · Docker Compose v5.5.0 · cargo 1.97.1 · host python 3.14.6
- Image backend dibangun dari `backend/Dockerfile` → `bottradingcrypto-backend:latest` (python:3.12-slim). Dependensi terpasang: fastapi 0.162, sqlmodel 0.0.48, pydantic 2.14, asyncpg 0.32, alembic 1.20, dll.
- Eksekusi self-check: `docker run --rm -v backend:/app -v .agents:/app/.agents:ro -w /app <image> python -m <modul>` (padanan `docker compose exec backend ...` di README, tanpa menyalakan seluruh stack).
- `.env`: **tidak dibuat** — tidak diperlukan untuk self-check pure. Compose stack penuh (Postgres/backend/frontend) **tidak** dinyalakan pada run ini.

## Hasil — Backend self-check (13/13 LULUS)
Kriteria lulus = modul mencetak `ok` DAN exit code 0 (diverifikasi terpisah dari pipe).

| Modul | Output | Exit | Status |
|---|---|---|---|
| src.risk.test_gate | ok | 0 | LULUS |
| src.risk.test_broker | ok | 0 | LULUS |
| src.risk.test_engine_client | ok | 0 | LULUS |
| src.risk.test_ledger | ok | 0 | LULUS |
| src.risk.test_burner_guard | ok | 0 | LULUS |
| src.agents.test_hermes | ok | 0 | LULUS |
| src.agents.test_wallet_scorer | ok | 0 | LULUS |
| src.agents.test_copy_trade | ok | 0 | LULUS |
| src.ingestion.test_aggregator | ok (+log DLQ TEST_SOURCE/PARSE_ERROR — perilaku uji) | 0 | LULUS |
| src.ingestion.test_heuristics | ok (+log backoff 429 attempt 1/2 — perilaku uji) | 0 | LULUS |
| src.ingestion.test_binance | ok (+log DLQ STALE/PARSE — perilaku uji) | 0 | LULUS |
| src.control.test_telegram_bot | ok (+log "Failed to send Telegram alert: 500" — jalur fail-safe diuji dgn token palsu) | 0 | LULUS |
| src.backtest.test_backtest | ok | 0 | LULUS |

Catatan: baris log tambahan (DLQ, backoff 429, Telegram 500) adalah **perilaku yang memang diuji** (dead-letter queue, backoff rate-limit, dan kegagalan kirim Telegram yang ditangani aman), tercetak sebelum `ok`. Bukan kegagalan.

## Hasil — Rust engine (`cargo test`, 4/4 LULUS)
```
test tests::test_drawdown_limit_rejected ... ok
test tests::test_daily_loss_limit_rejected ... ok
test tests::test_stale_data_rejected ... ok
test tests::test_valid_signal_passes ... ok
test result: ok. 4 passed; 0 failed
```

## Apa yang DITERBUKTIKAN run ini (naikkan status ke [B] terverifikasi, lingkup unit)
- **Risk Gate Python** (gate.py): 9 pintu + circuit breaker menolak/menerima sesuai input batas — **unit-level terverifikasi**.
- **Paper broker, ledger, burner_guard, engine_client (fail-closed), Hermes schema/fallback, wallet_scorer, copy_trade, ingestion aggregator/heuristics/binance, telegram bot, backtest anti look-ahead** — **unit-level terverifikasi**.
- **Rust `evaluate_candidate`**: 4 skenario (valid, drawdown, daily-loss, stale) — **unit-level terverifikasi**.

## Apa yang MASIH BELUM diuji (tetap [D]) — penting, jangan salah baca
Run ini **unit/self-check**, BUKAN integrasi/e2e. Masih belum terbukti:
- **Jalur HTTP API nyata** (21 endpoint di `03-api-inventory.csv`) — self-check tidak menyentuh FastAPI/ASGI, auth cookie, atau DB. Status di CSV tetap NOT_TESTED untuk level HTTP; hanya logika di baliknya yang teruji unit.
- **Risk Engine end-to-end** (signal→order→posisi→snapshot) terhadap Postgres sungguhan.
- **Parity Python↔Rust (F-02)**: masing-masing lulus unit test-nya **sendiri**, tetapi test unit memakai ekspektasi berbeda. Run ini **tidak** membuktikan keduanya setuju pada input identik — F-02 **belum tertutup**, malah dikonfirmasi: test Rust `recommended_allocation_pct=0.005` lolos di ambang `<=0.02`, sementara Python memakai `<=0.005`. Parity test lintas-implementasi masih diperlukan.
- **F-06**: fail-closed engine_client teruji unit, tetapi perilaku default (ENGINE_URL kosong) pada runtime penuh belum diuji.
- **F-07**: `test_wallet_scorer` membuktikan `calculate_wallet_metrics` benar, TETAPI **tidak** membuktikan `update_wallet_scores` dipanggil saat runtime — gap wiring tetap terbuka.
- **Migration** pada DB bersih — belum dijalankan.
- **Frontend** — tidak ada tooling, tidak dijalankan.

## Kesimpulan P0-1
Acceptance GAP-13 terpenuhi: seluruh self-check + cargo test dijalankan dan **17/17 hijau** (13 backend + 4 Rust). Ini menaikkan keyakinan atas **kebenaran logika unit** dari [A] ke [B]. Namun F-02/F-06/F-07 **belum** tertutup karena memerlukan uji lintas-implementasi / e2e / runtime, bukan unit test. Langkah berikut sesuai roadmap: P0-2 (parity Risk Gate) dan P1-3 (e2e + migration di Postgres disposable).
