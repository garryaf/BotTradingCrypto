# ROADMAP PRIORITAS PERBAIKAN — BOTTRADINGCRYPTO

**Tanggal:** 2026-10-26 · **Basis:** `OVERALL-APPLICATION-AUDIT-ID.md`, `OVERALL-GAP-ANALYSIS.csv`, `audit-tracker.csv`
**Catatan:** urutan ditetapkan agar aman dan efisien. Estimasi kompleksitas memakai skala **S/M/L**, bukan estimasi waktu presisi (lingkup implementasi belum semuanya diketahui).

## Status per 2026-10-26 (setelah remediasi)

Semua item asli P0–P3 di bawah **SELESAI** (rincian & bukti: `11-selfcheck-test-run.md`, `12-remediation-verification.md`, `13-final-remediation.md`). Teks "Status: PENDING" pada tiap item di bawah adalah status saat roadmap dibuat. Item baru dari verifikasi:

| Item | Temuan | Status | Butuh |
|---|---|---|---|
| P1-1 | GAP-02 rantai discovery → scoring → approval → copy-trade | **SELESAI** | Intake & approval manual (admin API + UI), riwayat dicatat (F-28), otoritas mint on-chain, harga/likuiditas DEXScreener; terbukti di `test_copy_trade_chain.py` (laporan 14) |
| P1-4 | F-16 sisa: paper execution sinyal copy-trade SPL | **OPEN** | Risk Gate menolak semua sinyal SPL (spread DEX tidak diketahui, fail-closed) sampai ada model spread/fee DEX + polling harga SPL untuk posisi terbuka — M |
| P1-6 | F-27 sinyal SELL Hermes dibuka sebagai long | **OPEN** | Keputusan: buang SELL / SELL = tutup long / dukung short — S |
| P2-9 | F-29 drawdown skor wallet selalu 0 | **OPEN** | Keputusan basis PnL & definisi drawdown — S/M |
| — | F-26 exit posisi (TP/SL) tidak pernah tereksekusi | **SELESAI** | Laporan 14 §3 |
| P1-5 | F-17 pintu 6 R:R ≥ 1:1.5 belum diterapkan | **OPEN** | Keputusan basis R:R, lalu Python + Rust + parity — S/M |
| P2-7 | F-18 eksekusi paper non-atomik | **OPEN** | flush + satu commit + test kegagalan — M |
| P2-8 | GAP-23 belum ada CI | **OPEN** | Pilih platform CI; jalankan 4 suite yang ada — S/M |
| P3-10 | F-24 advisory npm (Next 16 major) | **OPEN** | Upgrade terpisah — M |
| — | F-13, F-14, F-15, F-19, F-20, F-21, F-22, F-23, F-25 | **SELESAI** | — |
| — | F-06 kebijakan engine untuk fase live | **Keputusan pemilik** | — |

## Prinsip urutan
RC-3 (tidak ada test dijalankan) adalah pengganda: sampai self-check dijalankan, F-02/F-06/F-07 tidak bisa dibuktikan. Karena itu **menjalankan test yang sudah ada** mendahului sebagian remediasi, bukan menambah kode baru lebih dulu (sesuai Ponytail: pakai yang sudah ada).

---

## P0 — SAFETY-CRITICAL

### P0-1 · GAP-13 · Jalankan seluruh self-check + cargo test di Docker
- **Masalah:** nol bukti runtime; tidak bisa menilai F-02/F-06/F-07 tanpa ini.
- **Alasan prioritas:** prasyarat keselamatan — konfirmasi gate & eksekusi berperilaku seperti kode.
- **Dependensi:** Docker + Docker Compose, Postgres disposable (untuk test yang butuh DB), `cargo`.
- **Tindakan:** build image backend; jalankan `python -m src.risk.test_gate` dan seluruh `test_*` yang didokumentasikan README Step 5; jalankan `cd engine && cargo test`. Catat hasil per modul.
- **Test yang harus lulus:** semua self-check mencetak "ok"; 4 unit test Rust hijau.
- **Acceptance:** tabel hasil (lulus/gagal) terdokumentasi; baris NOT_TESTED di `03-api-inventory.csv`/`04-agent-workflow-matrix.csv` mulai terisi.
- **Kompleksitas:** S · **Status:** PENDING (butuh persetujuan menjalankan).

### P0-2 · GAP-01 (F-02) · Rekonsiliasi Risk Gate Python ↔ Rust
- **Masalah:** threshold & formula expectancy berbeda; Rust abaikan fee.
- **Alasan prioritas:** inti keselamatan trading; wajib benar sebelum fase apa pun yang mendekati live.
- **Dependensi:** P0-1 (parity test), keputusan sumber-kebenaran konstanta.
- **Tindakan (remediasi, bukan sekarang):** jadikan threshold satu sumber (mis. kirim dari payload/konfig ke Rust, atau samakan konstanta); samakan formula expectancy termasuk fee. Tahap audit: hanya **uji & dokumentasikan**, jangan ubah.
- **Test yang harus lulus:** parity — input identik → `passed` + nilai per-gate identik; boundary tiap gate; expectancy dengan fee konsisten.
- **Acceptance:** 0 ketidaksepakatan pada korpus input uji; "9 pintu" kedua implementasi identik.
- **Kompleksitas:** M · **Status:** PENDING.

---

## P1 — CRITICAL FUNCTIONAL GAPS

### P1-1 · GAP-02 (F-07) · Hubungkan scoring wallet ke runtime
- **Masalah:** `update_wallet_scores` tak pernah dipanggil → copy-trade inert.
- **Alasan prioritas:** fitur inti (copy-trading) tidak berfungsi di deployment bersih.
- **Dependensi:** P0-1; klarifikasi apakah approval wallet otomatis atau manual.
- **Tindakan:** tambahkan satu loop/scheduler pemanggil `update_wallet_scores` (pola sama seperti loop lain di `main.py`), ATAU dokumentasikan alur approval manual bila itu desain yang diinginkan.
- **Test yang harus lulus:** dengan data synthetic, wallet skor ≥ 70 otomatis `PENDING_REVIEW`; copy-trade dari wallet APPROVED menghasilkan `TradingSignal(PENDING)`.
- **Acceptance:** rantai discovery→scoring→promosi→copy-trade terbukti utuh pada data synthetic.
- **Kompleksitas:** S–M · **Status:** PENDING.

### P1-2 · GAP-03 (F-03) · Auth + scoping endpoint publik
- **Masalah:** `/signals` (global, tanpa auth) & `/backtest/run` (tanpa auth, `days` tak dibatasi).
- **Alasan prioritas:** trust boundary (Ponytail: jangan dipotong); privasi data + konsumsi resource.
- **Dependensi:** —.
- **Tindakan:** tambah `get_current_user` ke kedua endpoint; scope `/signals` ke user; batasi `days`.
- **Test yang harus lulus:** tanpa cookie → 401; user A tak melihat sinyal user B; `days` ekstrem ditolak.
- **Acceptance:** kedua endpoint hanya dapat diakses terautentikasi & terbatas.
- **Kompleksitas:** S · **Status:** PENDING.

### P1-3 · GAP-13 lanjut · Uji Risk Engine end-to-end + migration di DB disposable
- **Masalah:** jalur signal→risk→order→posisi→snapshot & migration belum pernah dijalankan.
- **Alasan prioritas:** membuktikan workflow inti sebelum staging.
- **Dependensi:** P0-1, Postgres disposable.
- **Tindakan:** `alembic upgrade head` pada DB kosong; masukkan sinyal synthetic; verifikasi order/posisi/snapshot & transisi status; uji rollback saat gagal; uji duplicate signal tidak membuat order ganda.
- **Test yang harus lulus:** e2e menghasilkan state benar; duplicate tidak menggandakan order; rollback bersih.
- **Acceptance:** 20 tabel ter-migrate; e2e paper-trade terbukti.
- **Kompleksitas:** M · **Status:** PENDING.

---

## P2 — IMPORTANT RELIABILITY & MAINTAINABILITY

### P2-1 · GAP-04 (F-04) · Hardening sesi & allowlist Telegram — S
Cookie `secure=True` di prod; verifikasi `message.from.id` vs `telegram_allowed_user_id`. Lulus: token tidak lewat HTTP polos; perintah dari user tak diizinkan ditolak.

### P2-2 · GAP-05 (F-06) · Kebijakan fail-closed eksplisit — S
Dokumentasikan bahwa default (ENGINE_URL kosong) memakai gate Python saja; tetapkan apakah engine wajib untuk live. Lulus: kebijakan tertulis + (bila engine aktif & down) semua sinyal ditolak.

### P2-3 · GAP-14 · Observability token/biaya + monitoring minimal — M
Hitung `cost_usd` dari respons gateway; tambah metrik dasar (latensi siklus, error rate). Lulus: `cost_usd` terisi; metrik dapat diamati.

### P2-4 · GAP-16 · Graceful shutdown — S
Tangani `CancelledError`/drain singkat agar order/commit tidak terpotong. Lulus: shutdown tidak memutus operasi di tengah (diuji).

### P2-5 · GAP-17 · Verifikasi dependency mencurigakan — S
Konfirmasi `framer-motion ^14.4.0` & `lucide-react ^1.60.0` resolve ke rilis nyata; pin bila perlu. Lulus: `npm ci` sukses + versi terverifikasi.

### P2-6 · GAP-18 · Satukan default model AI — S
Satu default valid & terverifikasi di config/.env/README. Lulus: konsisten di semua sumber.

---

## P3 — IMPROVEMENT

| ID | Gap | Tindakan | Kompleksitas |
|---|---|---|---|
| P3-1 | GAP-08 (F-05) | Validasi EmailStr + min_length password | S |
| P3-2 | GAP-09 (F-09) | Implementasi UI wallets atau tandai pending di RTM | M |
| P3-3 | GAP-11 (F-11) | Commit konfig Nginx + skrip UFW ke `deploy/` (jika belum di host) | S |
| P3-4 | GAP-12 (F-12) | Normalisasi penamaan + link README relatif | S |
| P3-5 | GAP-06 (F-01) | Selaraskan dokumen ke arsitektur orchestrator aktual | S |
| P3-6 | GAP-07 (F-10) | Turunkan status RTM yang overstated | S |
| P3-7 | GAP-09b (F-08) | Implementasi `/positions` Telegram atau hapus dari docs | S |
| P3-8 | GAP-15 | Rekonsiliasi 20 vs 21 tabel dengan DATA_DICTIONARY | S |
| P3-9 | — | Tooling test frontend (Playwright) — opsional, pemakaian pribadi | M |

---

## Ringkasan urutan efisien (end-to-end)
1. **P0-1** siapkan Docker + Postgres disposable, jalankan semua self-check + cargo test.
2. **P0-2** uji & reconcile parity Risk Gate (F-02).
3. **P1-1** wire & uji scoring wallet (F-07).
4. **P1-3** uji Risk Engine e2e + migration DB bersih.
5. **P1-2** hardening auth endpoint (F-03).
6. **P2-1..P2-6** reliability/observability/hardening.
7. **P3** sisanya.

> Dependency kritis sepanjang roadmap: Docker/Compose, Postgres 16 disposable, cargo, dan **tanpa kredensial produksi** — gunakan mock/testnet (Rule 4). Tidak ada load test sebelum stop conditions ditetapkan.
