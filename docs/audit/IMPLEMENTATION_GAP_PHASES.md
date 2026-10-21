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

### Peta gap (doc → kode)
| # | Gap | Dijanjikan di | Realita kode | Severity |
|---|-----|---------------|--------------|----------|
| G1 | Rust engine tidak ada | ADR-006, `RUST_ENGINE_INTEGRATION_SPEC.md`, `ARCHITECTURE_OVERVIEW.md` | `engine/` hanya `Cargo.lock` + `target/`; tak ada `Cargo.toml`/`src/` | Tinggi (arsitektural) |
| G2 | Python ↔ engine IPC client tidak ada | `RUST_ENGINE_INTEGRATION_SPEC.md` §3–5 | `grep ENGINE_URL / /evaluate / call_risk_engine` = 0 match | Tinggi |
| G3 | Wallet scoring engine tidak ada | FR-WLT-01, BR-01, `WALLET_DISCOVERY_FLOWCHART.mmd` | kolom `composite_score` dkk ada di `models.py`, tak ada kode hitung | Sedang |
| G4 | Copy-trading execution tidak ada | judul produk "Copy-Trading", `COPY_TRADING_FLOWCHART.mmd` | `grep copy_trad` = 0 match di backend | Sedang (scope) |
| G5 | Gap test + operasional (7 Partial, 2 Pending) | traceability matrix §11 | lihat Fase 4 di bawah | Rendah–Sedang |

### Catatan akurasi dokumen (bukan gap kode, tapi menyesatkan)
- `DOCUMENTATION_TASK_BACKLOG.md:159` menyatakan modul Rust `engine/src/risk_gate/mod.rs`
  "telah terbukti" evaluasi 292ns. **File itu tidak ada.** Angka 292ns adalah target, bukan
  hasil terukur. → ditangani di **PH1-T4**.
- `RUST_ENGINE_INTEGRATION_SPEC.md` jujur menyebut di §8 bahwa kode Rust belum ada; backlog
  di atas bertentangan dengan spec ini.

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

**Jalur B (bangun engine):**
- [ ] **PH1-T1b:** Scaffold crate Rust (`engine/Cargo.toml`, `src/main.rs`) + endpoint
      `POST /evaluate` sesuai kontrak `SignalCandidate`/`RiskEvaluationResult` (spec §4).
- [ ] **PH1-T2b:** Port 9 pintu Risk Gate ke Rust, paritaskan hasil dengan `risk/gate.py`
      (test lintas-bahasa: input sama → verdict sama).
- [ ] **PH1-T3b:** Implementasi `call_risk_engine()` di Python (httpx, timeout 10ms,
      **fail-closed** persis spec §5) + env `ENGINE_URL`/`ENGINE_TIMEOUT_MS` di `config.py`.
- [ ] **PH1-T4b:** Tambahkan service `engine` ke `docker-compose.yml` (spec §6.2), depends_on
      postgres healthy.

**Umum (kedua jalur):**
- [ ] **PH1-T4:** Perbaiki klaim palsu di `DOCUMENTATION_TASK_BACKLOG.md:159` (292ns "terbukti"
      → target, belum terukur). Gap akurasi, bukan kode.

### FASE 2 — Wallet Discovery Scoring (G3) — FR-WLT-01, BR-01

- [ ] **PH2-T1:** Implementasi mesin skoring wallet (disarankan `backend/src/agents/wallet_scorer.py`
      per saran matrix) yang mengisi `Wallet.composite_score`, `win_rate_pct`, `profit_factor`,
      `max_drawdown_pct` dari `wallet_observations` yang sudah terkumpul (`solana.py` sudah mengisi tabel ini).
- [ ] **PH2-T2:** Sambungkan hasil skor ke alur `WALLET_DISCOVERY_FLOWCHART.mmd` (watchlist/approval
      via `Wallet.status`, API sudah ada di `routes.py`).
- [ ] **PH2-T3:** Test: fixture observasi wallet → skor deterministik yang diharapkan (logika uang → wajib ada test).

### FASE 3 — Copy-Trading (G4) — keputusan scope dulu

- [ ] **PH3-T0 (keputusan):** Nama produk mengandung "Copy-Trading" dan ada
      `COPY_TRADING_FLOWCHART.mmd`, tapi **tidak ada** kode eksekusi copy-trade. Putuskan: apakah
      copy-trading masuk MVP, atau tetap pasca-MVP (konsisten dengan "Paper Trading First" ADR-004)?
- [ ] **PH3-T1 (jika in-scope):** Rancang jalur: wallet berskor tinggi (Fase 2) → usulan sinyal →
      Risk Gate yang **sama** (jangan bypass) → Paper Broker. Reuse Fase 4 yang sudah ada.
- [ ] **PH3-T2 (jika pasca-MVP):** Tandai eksplisit di `SCOPE_AND_NON_GOALS.md` bahwa auto-copy
      execution adalah non-goal MVP, agar judul produk tidak menyesatkan.

### FASE 4 — Tutup Gap Test & Operasional (G5) — dari traceability matrix §11

Test yang hilang (logika berisiko tanpa test = belum selesai menurut aturan ponytail):
- [ ] **PH4-T1:** `backend/src/ingestion/test_aggregator.py` — OHLCV aggregator + DLQ (FR-ING-03/04).
- [ ] **PH4-T2:** `backend/src/risk/test_ledger.py` — position compounding & HWM terisolasi (FR-SIM-02).
- [ ] **PH4-T3:** Test backoff 429 (mock) untuk `solana.py`/`binance.py` (AC-ING-04).
- [ ] **PH4-T4:** Integration test Binance ingestion (FR-MKT-01).

Fungsional kecil:
- [ ] **PH4-T5:** Hubungkan `SystemEvent` writer → `telegram_bot._send_message` agar notifikasi
      event otomatis (non-command) terkirim (FR-TG-01, AC-CTL-03). Kode `_send_message` sudah ada.

Operasional (butuh waktu nyata, bukan kode):
- [ ] **PH4-T6:** Jalankan RAM soak test 2 jam (`AC-OPS-01`, docker stats).
- [ ] **PH4-T7:** Jalankan DB restore drill FK-integrity (`AC-OPS-03`).

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
