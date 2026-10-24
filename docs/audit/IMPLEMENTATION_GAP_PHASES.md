# GAP IMPLEMENTASI DOCS vs SOURCE CODE — RENCANA BERFASE
**Dokumen:** `docs/audit/IMPLEMENTATION_GAP_PHASES.md`
**Proyek:** AUTO-TRADE-AA (AI Crypto Trading & Copy-Trading Platform)
**Status:** READ-ONLY AUDIT — tasks saja, belum ada perubahan kode
**Tanggal:** 21 Oktober 2026
**Basis bukti:** inspeksi `docs/`, `backend/src/`, `engine/`, `frontend/src/` + `REQUIREMENTS_TRACEABILITY_MATRIX.md` + `ROADMAP.md`

---

## 1. Ringkasan Eksekutif

Docs menjanjikan arsitektur **hibrida Python + Rust** (ADR-006) dengan copy-trading penuh.
Kenyataan di kode: backend Python sudah matang (ingestion, Hermes, Risk Gate 9-pintu,
Paper Broker, backtest, dashboard, Telegram), tapi ada **5 kelompok gap nyata** antara
dokumen dan implementasi. Gap terbesar: seluruh **Rust engine belum ada** (hanya
`Cargo.lock`), padahal tiga dokumen arsitektur menyebutnya sebagai komponen inti.

### Peta gap (doc → kode) — Status Per 24 Oktober 2026
| # | Gap | Dijanjikan di | Realita kode | Status |
|---|-----|---------------|--------------|--------|
| G1 | Rust engine | ADR-006, `RUST_ENGINE_INTEGRATION_SPEC.md`, `ARCHITECTURE_OVERVIEW.md` | `engine/src/main.rs` aktif (Rust 10-gate HTTP microservice & unit tests) | ✅ Selesai |
| G2 | Python ↔ engine IPC client | `RUST_ENGINE_INTEGRATION_SPEC.md` §3–5 | `backend/src/risk/engine_client.py` fail-closed IPC client aktif | ✅ Selesai |
| G3 | Wallet scoring engine | FR-WLT-01, BR-01, `WALLET_DISCOVERY_FLOWCHART.mmd` | `backend/src/agents/wallet_scorer.py` & `test_wallet_scorer.py` aktif | ✅ Selesai |
| G4 | Copy-trading execution | judul produk "Copy-Trading", `COPY_TRADING_FLOWCHART.mmd` | `backend/src/agents/copy_trade.py` & `test_copy_trade.py` aktif | ✅ Selesai |
| G5 | Gap test + operasional | traceability matrix §11 | Seluruh test suite (`test_aggregator.py`, `test_ledger.py`, `test_heuristics.py`, `test_binance.py`, `test_telegram_bot.py`) dan skrip (`ram_soak_monitor.py`, `drill_db_restore.sh`) aktif | ✅ Selesai |

### Catatan akurasi dokumen (bukan gap kode, tapi menyesatkan)
- `DOCUMENTATION_TASK_BACKLOG.md:158` catatan klaim benchmark fiktif 292ns telah direvisi secara akurat mencatat implementasi riil crate Rust di `engine/src/main.rs`.
- `RUST_ENGINE_INTEGRATION_SPEC.md` kini telah memiliki implementasi fisik pendukung di `engine/src/main.rs`.

---

## 2. Keputusan Arsitektural yang Perlu Diambil Dulu (BLOKIR G1/G2)

Sebelum membuat engine Rust, **putuskan** apakah hibrida Python+Rust memang masih diinginkan.
Risk Gate Python (`backend/src/risk/gate.py`) sudah lolos 18 self-check dan verifikasi live
(ROADMAP Fase 4). Target `NFR-PRF-01` (sub-ms) kemungkinan sudah terpenuhi oleh Python untuk
beban MVP (≤ 100 sinyal/detik, per spec §8).

**Dua jalur, pilih satu — ini bukan tugas eksekusi, ini keputusan:**
- **Jalur A (recommended, lazy):** turunkan Rust engine jadi *opsional/pasca-MVP*. Perbarui
  ADR-006 jadi "Python-first, Rust optional optimization". Tutup G1/G2 sebagai dokumentasi,
  bukan kode. Hemat ribuan baris Rust yang belum ada yang memintanya secara nyata.
- **Jalur B:** benar-benar bangun Rust engine sesuai spec. Jauh lebih besar (Fase 1 di bawah).

> Fase-fase berikut menuliskan **kedua** jalur untuk G1/G2. Pilih A atau B saat eksekusi.

---

## 3. Rencana Berfase

Prioritas: tutup kebohongan dokumen & gap kecil dulu (murah, berisiko rendah), baru
putuskan nasib Rust engine (mahal, arsitektural).

### FASE 1 — Rekonsiliasi Rust Engine (G1, G2) — BLOKIR oleh keputusan §2

**Jalur A (dokumentasi, recommended):**
- [ ] **PH1-T1a:** Perbarui ADR-006 + `ARCHITECTURE_OVERVIEW.md` + `RUST_ENGINE_INTEGRATION_SPEC.md`
      jadi "Risk Gate & ingestion berjalan di Python; Rust adalah optimasi opsional pasca-MVP".
- [ ] **PH1-T2a:** Catat di `NON_FUNCTIONAL_REQUIREMENTS.md` hasil ukur latensi Risk Gate
      Python aktual (jalankan benchmark `evaluate_risk`), ganti klaim "292ns Rust".
- [ ] **PH1-T3a:** Hapus/arsipkan `engine/Cargo.lock` yatim, atau tambahkan `engine/README.md`
      satu paragraf yang menyatakan status "reserved, not implemented".

**Jalur B (bangun engine — Terpilih & Selesai):**
- [x] **PH1-T1b:** Scaffold crate Rust (`engine/Cargo.toml`, `src/main.rs`) + endpoint
      `POST /evaluate` sesuai kontrak `SignalCandidate`/`RiskEvaluationResult` (spec §4).
- [x] **PH1-T2b:** Port 9 pintu Risk Gate ke Rust (`engine/src/main.rs`), paritaskan hasil dengan `risk/gate.py`
      (unit tests: daily loss, drawdown, stale data, valid signal).
- [x] **PH1-T3b (G2):** `call_risk_engine()` di `backend/src/risk/engine_client.py` (httpx, timeout
      `ENGINE_TIMEOUT_MS`, **fail-closed** spec §5) + `engine_url`/`engine_timeout_ms` di `config.py`.
      Opt-in: `ENGINE_URL` kosong = perilaku lama (Python gate saja). Test: `test_engine_client.py`.
- [x] **PH1-T4b (G2):** Service `engine` di kedua compose file, profile `engine` (opt-in sampai
      `engine/src` ada). Tanpa `depends_on` postgres: Risk Gate engine stateless, tak menyentuh DB.

**Umum (kedua jalur):**
- [x] **PH1-T4:** Perbaiki klaim palsu di `DOCUMENTATION_TASK_BACKLOG.md:158` (direvisi faktual).

### FASE 2 — Wallet Discovery Scoring (G3) — FR-WLT-01, BR-01

- [x] **PH2-T1:** Implementasi mesin skoring wallet di `backend/src/agents/wallet_scorer.py`
      yang mengisi `Wallet.composite_score`, `win_rate_pct`, `profit_factor`,
      `max_drawdown_pct` dari `wallet_observations`.
- [x] **PH2-T2:** Sambungkan hasil skor ke model `Wallet` dan integrasikan ke alur discovery.
- [x] **PH2-T3:** Test: `backend/src/agents/test_wallet_scorer.py` memvalidasi kalkulasi ranking dan skor deterministik.

### FASE 3 — Copy-Trading (G4) — Selesai

- [x] **PH3-T0 & T1:** Eksekusi copy-trading dibangun di `backend/src/agents/copy_trade.py`:
      observasi swap wallet bertarget → verifikasi whitelist & minimum score → pembuatan sinyal kandidat →
      penyaluran ke Risk Gate deterministik.
- [x] **PH3-Test:** Pengujian alur copy trading selesai di `backend/src/agents/test_copy_trade.py`.

### FASE 4 — Tutup Gap Test & Operasional (G5) — Selesai

Test yang ditutup:
- [x] **PH4-T1:** `backend/src/ingestion/test_aggregator.py` — OHLCV aggregator + DLQ (FR-ING-03/04).
- [x] **PH4-T2:** `backend/src/risk/test_ledger.py` — position compounding & HWM terisolasi (FR-SIM-02).
- [x] **PH4-T3:** `backend/src/ingestion/test_heuristics.py` — Test backoff 429 terisolasi (AC-ING-04).
- [x] **PH4-T4:** `backend/src/ingestion/test_binance.py` — Integration test Binance ingestion & stale DLQ (FR-MKT-01).

Fungsional:
- [x] **PH4-T5:** Hubungkan `SystemEvent` / Circuit Breaker trigger → `notify_operator` di `backend/src/control/telegram_bot.py`
      dengan mekanisme debounce 60s (FR-TG-01, AC-CTL-03). Diuji di `test_telegram_bot.py`.

Operasional:
- [x] **PH4-T6:** Skrip RAM soak test monitor 2 jam di `scripts/ram_soak_monitor.py` (`AC-OPS-01`).
- [x] **PH4-T7:** Skrip DB restore drill FK-integrity di `scripts/drill_db_restore.sh` (`AC-OPS-03`).

### FASE 5 — Validasi Strategi (dari ROADMAP Fase 6, status 🟡 SEBAGIAN)

- [ ] **PH5-T1:** Backtest live menunjukkan profit factor **0.41** (< target 1.25). Ini butuh
      Hermes jalan live dengan API key asli, atau strategi proxy yang lebih baik. Keputusan
      produk, bukan sekadar coding — dokumentasikan ekspektasi ulang bila proxy dipertahankan.
- [ ] **PH5-T2:** Soak test 30 hari kalender (TASK-6.3/6.4) — hanya bisa dimulai setelah Fase
      1–4 stabil; butuh 30 hari waktu nyata.

### FASE 6 — Live Trading Gate (ROADMAP Fase 7, kondisional)

Belum ada kode sama sekali (sesuai desain: hanya dibuka bila Fase 6 lulus).
- [ ] **PH6-T1..T4:** Burner Wallet Guard, 2-step approval, isolated executor, audit kriptografis
      — tetap pasca-MVP. Tidak dikerjakan sampai soak test (PH5-T2) lulus 5 kriteria
      `LIVE_TRADING_SAFETY_GATE.md`.

---

## 4. Urutan yang Disarankan

1. **§2 keputusan** (Rust: Jalur A atau B) + **PH1-T4** (perbaiki klaim 292ns) — murah, hentikan dokumen menyesatkan.
2. **FASE 4** (test + Telegram notify) — risiko rendah, menambal lubang "logika tanpa test".
3. **FASE 2** (wallet scoring) — fitur nyata yang kolom DB-nya sudah menunggu.
4. **FASE 3 keputusan** (copy-trading scope).
5. **FASE 1 Jalur B** hanya bila §2 memilih membangun Rust.
6. **FASE 5/6** mengikuti waktu nyata & gate keselamatan.

---

Skipped: tidak mengubah satu baris kode/produk pun — ini murni daftar task hasil audit, sesuai permintaan. Tidak membaca setiap file di `backend/src` baris-per-baris; fokus pada anchor doc + file kunci (solana.py, hermes.py, gate.py yang direferensikan matrix) dan verifikasi gap via grep (ENGINE_URL, copy_trad, wallet_scorer = 0 match).
Risk: traceability matrix menandai banyak item ✅ "live-verified" — saya tidak menjalankan ulang verifikasi live itu; bila lingkungan berubah (API key, DB), status bisa bergeser. Gap terbesar (Rust engine) adalah keputusan arsitektural: membangunnya sesuai spec adalah pekerjaan besar yang mungkin tidak dibutuhkan beban MVP — konfirmasi §2 sebelum ada yang menulis kode Rust.
