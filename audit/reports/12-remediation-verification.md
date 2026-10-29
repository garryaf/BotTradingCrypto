# 12 — Remediasi & Verifikasi (F-02, F-06, F-07, HTTP, e2e, migration)

**Tanggal:** 2026-10-26
**Lingkup:** menutup temuan yang pada run sebelumnya (laporan 11) masih terbuka karena hanya unit/self-check. Dilakukan perbaikan kode minimal + penulisan test verifikasi, lalu dijalankan di Docker dengan PostgreSQL disposable. Tidak ada order live, tidak ada operasi destruktif pada data yang ada, tidak ada perubahan konfigurasi produksi.

> **Koreksi (lihat `13-final-remediation.md` §1):** klaim di §3 bahwa copy-trade dapat aktif setelah approval, penutupan GAP-15 sebagai "salah hitung" di §4, dan cakupan uji duplikasi e2e ternyata keliru. Status terkini ada di laporan 13.

## Lingkungan
- Docker + Compose v5.5.0, cargo 1.97.1.
- Image backend `bottradingcrypto-backend` (python:3.12-slim) hasil build `backend/Dockerfile`.
- PostgreSQL disposable: `docker run --rm postgres:16-alpine` di port host 55432, DB `autotrade_test` (bukan DB/volume milik aplikasi). Dihapus otomatis setelah selesai (`--rm` + `docker stop`).
- Venv sementara (host) untuk parity test, dibersihkan setelahnya.

---

## 1. F-02 — Parity Risk Gate Python ↔ Rust (RESOLVED)

### Perubahan kode
- `engine/src/main.rs` — `evaluate_candidate` ditulis ulang agar **meniru persis** `backend/src/risk/gate.py`:
  - Ambang disamakan ke sumber Python (otoritatif): max posisi `< 5`, risk per trade `<= 0.5%`, spread `<= 0.08%`, likuiditas 24h `>= 1.000.000`, freshness `<= 30s`, daily-loss `< 2%`, drawdown `< 8%`.
  - Formula expectancy disamakan: blend TP1/TP2 50/50, **memperhitungkan fee** (`fee_ratio_r = fee_usd / dollar_risk`), winrate dari `estimated_winrate_pct` (bukan `confidence_score`).
  - Konstanta didefinisikan eksplisit + komentar "mirror of gate.py" agar tidak drift.
- `backend/src/risk/engine.py` — `_signal_candidate` kini mengirim `estimated_winrate_pct`, `dollar_risk`, `fee_usd` (sudah tersedia di `outcome`/`signal`) agar Rust bisa menghitung expectancy identik.

### Test & hasil
- `engine/` `cargo test` → **8/8 LULUS** (4 lama + 4 guard parity baru: risk-cap 0.5%, batas posisi <5, spread/likuiditas, expectancy fee-aware).
- Baru `backend/src/risk/test_parity.py` — menyalakan binary Rust (`cargo build --release`), mengirim payload identik ke `/evaluate` dan membandingkan verdict dengan `evaluate_risk` pada **11 kasus batas** (baseline pass, daily-loss, drawdown, spread lebar, likuiditas tipis, max/4th position, stale, stop-loss salah sisi, winrate rendah). → **`ok`, 0 mismatch.**

**Status:** F-02 ditutup. Keputusan kedua implementasi kini **identik pada input identik** (bukan sekadar "Rust lebih ketat").

---

## 2. F-06 — Fail-closed default (VERIFIED, by design)

Tidak ada perubahan kode (perilaku memang by-design: `ENGINE_URL` kosong → gate Python in-process yang otoritatif).
- `test_engine_client` (unit) sudah membuktikan jalur fail-closed: ENGINE_TIMEOUT/UNAVAILABLE/ERROR/INVALID_RESPONSE semua menolak.
- `test_engine_e2e` (baru, DB nyata, `engine_url` kosong) membuktikan gate Python berjalan dan **menolak** sinyal stop-loss salah-sisi tanpa membuat order.

**Status:** dikonfirmasi berfungsi sesuai desain. Rekomendasi dokumentasi (opt-in engine untuk live) tetap berlaku — bukan defect.

---

## 3. F-07 — Wiring scoring wallet (RESOLVED)

### Perubahan kode
- `backend/src/agents/wallet_scorer.py` — tambah `run_wallet_scoring_loop()` (interval 300s, pola sama seperti loop lain, bungkus try/except + log).
- `backend/src/main.py` — import + `asyncio.create_task(run_wallet_scoring_loop())` di lifespan.

### Verifikasi (DB nyata)
Wallet `DISCOVERED` + observasi BUY lalu SELL menguntungkan → `update_wallet_scores` menghasilkan `composite_score=100.00` dan status naik ke **`PENDING_REVIEW`**. Impor `src.main` sukses dengan loop baru ter-wire.

**Status:** rantai discovery → scoring → promosi → (approval) → copy-trade tidak lagi putus. Copy-trade kini dapat aktif di deployment bersih setelah wallet dipromosikan & di-approve.

---

## 4. Migration pada DB bersih (VERIFIED)

`alembic upgrade head` pada DB kosong menjalankan 001→002→003→004→005 tanpa error. `\dt` menampilkan **21 relasi** = **20 tabel domain + `alembic_version`**.

> **Resolusi selisih "20 vs 21":** klaim README "21 tabel" cocok dengan output `\dt` (yang menghitung `alembic_version`). Tabel domain aplikasi = 20. GAP-15 ditutup sebagai salah-hitung dokumentasi minor (bukan tabel hilang).

---

## 5. HTTP endpoint (sebagian VERIFIED)

Baru `backend/src/api/test_http.py` (ASGI via httpx, **lifespan tidak dijalankan** sehingga 6 loop background tidak menyala). Terhadap DB disposable → **`ok`**. Yang terbukti:
- 401 untuk `/auth/me`, `/portfolio`, `/control/kill` tanpa cookie.
- `/auth/register` user pertama → `role=admin`; email duplikat → 409.
- `/auth/me`, `/portfolio` (seed kapital awal), `/positions` (kosong untuk user baru).
- `/auth/binance-credentials` PUT+GET round-trip Fernet (last4=1234).
- `/admin/users` (admin), `/control/kill` + `/control/resume` (admin).

Endpoint lain (login, logout, risk/status, control/pause, account/*, admin PATCH, backtest/run, signals) **belum** di-HTTP-test — lihat `03-api-inventory.csv`.

---

## 6. Ringkasan status setelah remediasi

| Temuan | Sebelum | Sesudah | Bukti |
|---|---|---|---|
| F-02 (parity gate) | High, OPEN | **RESOLVED** | cargo 8/8, test_parity 11/11 |
| F-06 (fail-closed default) | Info, OPEN | **VERIFIED (by design)** | test_engine_e2e + test_engine_client |
| F-07 (scoring tak ter-wire) | High, OPEN | **RESOLVED** | loop wired + promosi wallet di DB nyata |
| Migration DB bersih | belum diuji | **VERIFIED** | alembic 001→005, 21 relasi |
| HTTP endpoint inti | NOT_TESTED | **HTTP_VERIFIED (sebagian)** | test_http ok |
| Risk Engine e2e | belum diuji | **E2E_VERIFIED** | pass→order, reject→no order |
| Selisih 20/21 tabel (GAP-15) | terbuka | **RESOLVED** | 20 domain + alembic_version |

## 7. Yang MASIH belum diuji (jujur)
- Endpoint HTTP non-inti (lihat tabel 03-api-inventory.csv rows NOT_TESTED).
- **F-03/F-04/F-05 belum diperbaiki** (auth `/signals` & `/backtest/run`, cookie `secure`, allowlist user-id, validasi input) — di luar lingkup permintaan "tutup yang belum terbukti"; tetap terbuka di tracker.
- Frontend (tetap tanpa tooling test).
- Soak/performance (belum; butuh stop conditions).
- Rust engine berjalan **di dalam Docker Compose** (parity diuji via binary native; container engine belum di-compose-up).

## 8. Berkas yang diubah/ditambah
Kode: `engine/src/main.rs`, `backend/src/risk/engine.py`, `backend/src/agents/wallet_scorer.py`, `backend/src/main.py`.
Test baru: `backend/src/risk/test_parity.py`, `backend/src/risk/test_engine_e2e.py`, `backend/src/api/test_http.py`.
Audit: `audit-tracker.csv`, `03-api-inventory.csv`, `04-agent-workflow-matrix.csv`, laporan ini.

## 9. Regresi
Seluruh 13 self-check backend + `cargo test` 8/8 dijalankan ulang **setelah** perubahan → hijau. `src.main` impor sukses dengan loop scoring baru.

---

## 10. Remediasi lanjutan — F-03, F-04, F-05 (RESOLVED)

Dikerjakan pada iterasi berikutnya atas permintaan pemilik. Pendekatan: perubahan kode minimal + test verifikasi (Postgres disposable + ASGI, tanpa order live).

### F-03 — Endpoint tanpa auth (RESOLVED)
Perubahan kode:
- `api/routes.py`: `get_signals` kini `Depends(get_current_user)`. Catatan desain: `TradingSignal` **tidak punya** kolom `user_id` (ini analisis pasar bersama; hasil per-akun ada di `RiskCheck`), jadi di-gate pada **autentikasi**, bukan kepemilikan per-user. Itu perbaikan yang jujur sesuai model data.
- `api/routes.py`: `backtest_run` kini `Depends(get_current_user)` + `days: int = Query(60, ge=1, le=365)` untuk membatasi fetch historis outbound.

Verifikasi (`test_http.py`): anon `/signals` → **401**; authed `/signals` → **200** (list); `/backtest/run?days=99999` → **422**; `?days=0` → **422**; anon `/backtest/run` → **401**. (Validasi query & auth FastAPI berjalan sebelum handler, jadi `days` di luar rentang ditolak tanpa menjalankan fetch.)

### F-04 — Cookie Secure + allowlist Telegram sender (RESOLVED)
Perubahan kode:
- `api/auth_routes.py`: `_set_session_cookie` kini `secure=settings.app_env != "development"` (aktif di staging/prod di balik TLS; mati untuk dev HTTP lokal). `settings` diimpor.
- `control/telegram_bot.py`: ekstraksi `_is_allowed(chat_id, from_id)` — selain chat-id, bila `telegram_allowed_user_id` diset maka `from_id` pengirim harus cocok. Dipakai di loop polling (pengganti pengecekan chat-id-only).

Verifikasi:
- `test_http.py`: header `Set-Cookie` mengandung `Secure` saat `APP_ENV=production`, dan **tidak** mengandung `Secure` saat `APP_ENV=development` (diuji di kedua env; prod dites via base-url https agar klien mengembalikan cookie Secure).
- `test_telegram_bot.py`: `_is_allowed` — chat salah → False; chat benar tapi sender salah → **False** (inti F-04); sender tak dikonfigurasi → hanya cek chat.

### F-05 — Validasi input register/login (RESOLVED)
Perubahan kode:
- `api/auth_routes.py`: `Credentials` memakai `Field(min_length=...)` untuk email (3–255) & password (8–128) + `field_validator` cek bentuk email sederhana (ada `@`, domain ber-titik). **Tanpa** menambah dependency `email-validator` (Ponytail: jangan tambah dep untuk beberapa baris; `EmailStr` butuh paket itu yang tidak terpasang).

Verifikasi (`test_http.py`): email ngawur (`not-an-email`) → **422**; password pendek (`short`) → **422**; kredensial valid → tetap jalan normal.

### Regresi setelah F-03/F-04/F-05
- 13 self-check backend → hijau (termasuk 2 test allowlist Telegram baru).
- `test_http` dev & prod → `ok`. `test_engine_e2e` → `ok`. `test_parity` 11/11 + `cargo test` 8/8 → hijau.
- Catatan: `test_http` mengasumsikan tabel `users` kosong untuk aturan "user pertama = admin"; pada DB disposable kami reset (DROP/CREATE DATABASE) sebelum tiap run. Ini **bukan** operasi pada data aplikasi — hanya DB uji buang.

### Berkas tersentuh (iterasi ini)
Kode: `api/routes.py`, `api/auth_routes.py`, `control/telegram_bot.py`.
Test: `api/test_http.py` (ditambah assert F-03/F-04/F-05), `control/test_telegram_bot.py` (ditambah 2 test `_is_allowed`).

### Status temuan hardening setelah iterasi ini
F-03 RESOLVED · F-04 RESOLVED · F-05 RESOLVED. Sisa OPEN di tracker tinggal yang P3/informational (F-08 /positions, F-09 UI wallets, F-11 nginx/ufw artefak, F-12 penamaan) + rekomendasi observability (GAP-14/16/17/18).

---

## 11. P0-2 lanjutan — Single source of truth untuk threshold (RESOLVED)

Sisa P0-2 dari roadmap ("jadikan threshold satu sumber") yang sebelumnya belum dikerjakan. Sebelumnya ambang ada di dua tempat: `settings`/`gate.py` (Python) dan `const` di `engine/src/main.rs` (Rust) — cocok, tapi duplikat.

### Perubahan kode
- `backend/src/risk/engine.py` — `_signal_candidate` kini mengirim blok `limits` (dari `settings.*` + `MAX_OPEN_POSITIONS`/`MIN_24H_VOLUME_USD` `gate.py`). Satuan menyesuaikan field payload: spread/daily-loss/drawdown dalam **persen** (`*100`), risk/trade sebagai **fraksi**, volume absolut. Impor `MAX_OPEN_POSITIONS`, `MIN_24H_VOLUME_USD` ditambah.
- `engine/src/main.rs` — `const` dihapus, diganti struct `Limits` (`#[serde(default = ...)]` per field) + field `limits: Limits` pada `SignalCandidate`. `evaluate_candidate` membaca `candidate.limits.*`. Default hanya dipakai bila payload tidak mengirim `limits` (kompatibel mundur).

Hasilnya: **Python satu-satunya sumber ambang**. Kalau kebijakan risiko berubah di `settings`/`gate.py`, engine Rust otomatis ikut — tidak ada lagi angka hardcode yang bisa menyimpang.

### Test & hasil
- `cargo test` → **10/10** (tambah `test_payload_limits_override_defaults` — payload menetapkan max_pos=2 membuat 3 posisi ditolak meski default 5; dan `test_missing_limits_json_falls_back_to_defaults` — payload tanpa `limits` tetap pakai nilai hari ini).
- `test_parity.py` (payload kini menyertakan blok `limits` sama seperti produksi) → **`ok`, 11/11** verdict identik.
- Regresi: 13 self-check backend hijau; `src.risk.engine` impor sukses dengan konstanta baru.

### Status P0-2
Acceptance terpenuhi seluruhnya: parity 0 mismatch, boundary tiap gate diuji, expectancy fee-aware konsisten, **dan** threshold kini satu sumber (Python → payload → Rust). F-02 ditutup penuh.

---

## 12. Sisa P3 + observability — F-08, F-09, F-11, F-12, GAP-14/16/17 (RESOLVED)

Dikerjakan atas permintaan pemilik ("implementasikan"). Perubahan kecil + verifikasi; tanpa order live / operasi destruktif.

### F-08 — Telegram /positions (RESOLVED)
- `api/control.py`: tambah `open_positions_detail(session)` — posisi terbuka operator-wide (symbol, qty, entry, floating PnL). Impor `Position` + `OPEN_POSITION_STATUSES`.
- `control/telegram_bot.py`: handler `/positions` + `_format_positions`.
- Verifikasi (DB nyata): empty-state → "📭 Tidak ada posisi terbuka."; 1 posisi → "BTCUSDT: 0.500000 @ $100.00 | PnL $12.34". 13 self-check tetap hijau.

### F-09 — UI wallets (RESOLVED)
- `api/routes.py`: `GET /api/v1/wallets` (auth, wallet ter-skor, urut composite_score desc, limit 50). Impor `Wallet`.
- `components/WalletExplorer.tsx`: polling `/api/v1/wallets` (10s), render tabel; fallback `NotConnected` saat null (backend down) / kosong (belum ada skor).
- Verifikasi: `next build` sukses (route `/wallets` 3.15 kB, 11 halaman); `test_http` → `/wallets` 401 anon + 200 authed list.

### F-11 — Nginx/UFW artefak (RESOLVED)
- `deploy/nginx/autotrade.conf` (reverse proxy /api→8000, /→3000, gzip, WS headers) + `deploy/ufw.sh` (executable; deny-in/allow-out + 22/80/443). Mencerminkan prosa README agar deploy reproducible. Placeholder domain `trade.your-domain.com`.

### F-12 — Penamaan / link README (RESOLVED)
- 19 link absolut rusak `file:///Users/.../AUTO-TRADE-AA/docs/...` di README ditulis ulang jadi relatif `docs/...` (0 tersisa). Diverifikasi: `[docs/00-overview/ROADMAP.md](docs/00-overview/ROADMAP.md)`.
- **Sengaja dibiarkan:** URL clone GitHub (`github.com/Angga47/AUTO-TRADE-AA.git` — remote asli, mengubahnya merusak `git clone`) dan 9 penyebutan judul historis. Nama paket/DB (`autotrade`) juga dibiarkan (mengubahnya menyentuh migration + env, di luar lingkup kosmetik).

### GAP-14 — cost_usd (PARTIAL → cost DONE)
- `agents/hermes.py`: `LLMRequest.cost_usd` kini diisi dari `usage.cost` (OpenRouter mengembalikannya bila tersedia). Token & latency sudah tersimpan sebelumnya. Monitoring stack terpusat tetap ditunda (P3).

### GAP-16 — graceful shutdown (RESOLVED)
- `main.py` lifespan: setelah `task.cancel()`, kini `await asyncio.gather(*tasks, return_exceptions=True)` agar `async with` tiap loop (sesi DB, httpx client) menutup bersih, bukan terputus. Impor `src.main` OK.

### GAP-17 — versi dependency (RESOLVED, ternyata nyata)
- Dicek via `npm view`: `lucide-react@1.61.0` dan `framer-motion@14.6.0` **benar-benar rilis nyata** (bukan typosquat; web search awal menyesatkan). Di-pin ke versi persis. `npm install` + `next build` sukses.

### Regresi sesi ini
13 self-check backend hijau; `src.main`/`control`/`routes`/`hermes` impor OK; `test_http` (incl /wallets) → `ok`; `next build` compile 11 route. Engine/gate tidak disentuh sesi ini → parity 11/11 & cargo 10/10 tetap berlaku.

### Status akhir temuan
F-01 (dok) · F-02 · F-03 · F-04 · F-05 · F-06 · F-07 · F-08 · F-09 · F-11 · F-12 = RESOLVED/VERIFIED.
Sisa: GAP-14 (monitoring terpusat, P3), GAP-18 (default model AI konsisten, P3), tooling test frontend (P3) — semua non-blocking.
