# 13 — Remediasi Akhir, Koreksi, dan Temuan Baru

**Tanggal:** 2026-10-26
**Lingkup:** mengerjakan semua saran yang masih terbuka (GAP-14 monitoring, GAP-18 default model, tooling test frontend, pelonggaran validasi login, F-01 & F-10 dokumentasi, sisa P1-3) plus temuan baru yang muncul saat memverifikasinya. Tanpa order live, tanpa kredensial produksi, tanpa menyentuh stack compose/volume/data milik pengguna. Semua container uji dibuat dan dihapus oleh skrip.

---

## 1. Koreksi atas laporan dan ringkasan sebelumnya

Ini mengubah kesimpulan, jadi dicatat eksplisit:

1. **F-01 sempat diklaim RESOLVED** di ringkasan sesi sebelumnya, padahal dokumentasinya belum diubah. Sekarang benar-benar dikerjakan (§2).
2. **Laporan 12 §3 menyatakan copy-trade "dapat aktif setelah wallet dipromosikan & di-approve".** Itu salah. Rantai copy-trade masih tidak bisa berjalan end-to-end karena beberapa sebab independen (F-16, §4).
3. **GAP-15 ("20 vs 21 tabel") ditutup sebagai salah hitung.** Itu salah. Kamus data memang hanya memuat 18 tabel; `users` dan `binance_credentials` (migrasi 004/005) tidak terdokumentasi. Sekarang ditambahkan.
4. **Kriteria P1-3 "duplicate signal tidak membuat order ganda" tidak pernah diuji**, meski docstring `test_engine_e2e.py` mengklaimnya. Saat diuji, ternyata memang rentan (F-13). Sekarang diperbaiki dan diuji.
5. **Klaim "test parity menangkap perubahan di salah satu sisi" terlalu luas.** Test parity hanya menguji rumus Rust dengan payload buatannya sendiri; builder payload produksi dan framing HTTP tidak tersentuh. E2E dengan engine sungguhan (mode `up`) kini menguji jalur itu — dan langsung menemukan F-20.

---

## 2. Saran yang dikerjakan

| Item | Perubahan | Verifikasi |
|---|---|---|
| GAP-14 monitoring | `/api/v1/health` melaporkan status tiap loop (`running/exited/crashed/cancelled`) dan `degraded` bila DB putus atau ada loop crash; crash loop kini tercatat di log. `GET /api/v1/admin/metrics`: agregat 24 jam (LLM: request, error, token, `cost_usd`, latensi; agent run; sinyal; risk check; DLQ; event kritis) | `test_main` (4 status task), `test_http` (health + metrics, 401 anon) |
| GAP-18 default model | `anthropic/claude-haiku-5.5` di `config.py`, `.env.example`, README; catatan di OPEN_QUESTIONS Q-12. Dua id lama (`claude-3.5-haiku/-sonnet`) **tidak ada** di OpenRouter | `GET https://openrouter.ai/api/v1/models` |
| Tooling test frontend | Playwright 1.64.1 (dev dependency, di-pin) + `npm run test:e2e`; 7 test hermetic (API & Binance di-mock, tanpa backend/jaringan) | 7/7 lulus; test kill switch **gagal** terhadap komponen lama dari git HEAD (bukti test menangkap bug) |
| Login vs register | `Credentials` (login, hanya dibatasi) dan `Registration` (policy email + min 8) dipisah, agar perubahan policy tidak mengunci akun lama | `test_http`: password salah pendek → 401, bukan 422 |
| F-01 | `AI_AGENT_ARCHITECTURE.md` §0 memetakan setiap peran ke kode yang berjalan; README menautkannya | Diperiksa terhadap `hermes.py` |
| F-10 | RTM: BR-01, FR-WLT-03, FR-AI-03, FR-RSK-01, FR-UI-02 → Partial; nama fungsi & referensi test yang salah diperbaiki; rekap dihitung ulang dari baris (53 baris: 48 ✅ / 5 ⚠️ — sebelumnya "48/48 100%" dengan FR salah hitung 20 padahal 25) | Diperiksa baris per baris |
| F-12 lanjutan | 92 link absolut rusak di 10 dokumen `docs/` ikut diperbaiki (total 111) | 116 link relatif dicek otomatis, 0 tidak resolve |
| GAP-15 | Kamus data: Seksi 0 `users` & `binance_credentials`, kolom `user_id` di 3 tabel, interval OHLCV aktual (`M1/M5/H1`); ERD ditambah dua entitas; README "21 entitas" → "20 tabel domain + alembic_version" | DB kosong setelah migrasi: 20 tabel domain |
| P1-3 sisa | Uji duplikasi, uji engine `up`/`down` di DB nyata, skrip integrasi satu perintah | §5 |
| Pelengkap | RiskGatePanel membaca ambang dari backend; KillSwitch & Settings menampilkan kegagalan | Playwright |

---

## 3. Temuan baru — sudah diperbaiki

| ID | Sev. | Masalah | Perbaikan | Bukti |
|---|---|---|---|---|
| F-13 | High | Sinyal yang ditawarkan ulang (crash/restart sebelum `DISPATCHED`) bisa membuka order kedua untuk akun yang sama | Guard idempoten di `_process_signal` (satu verdict per akun per sinyal) | e2e: proses ulang → tetap 1 RiskCheck, 1 order |
| F-14 | High | Satu error DB "meracuni" sesi; query berikutnya (di luar `try`) melempar dan **mematikan loop risk engine** — SL/TP berhenti dipantau tanpa tanda | `_dispatch_pending`: rollback lalu akhiri ronde; retry aman karena idempoten | e2e: `SELECT 1/0` disuntikkan → loop bertahan, sinyal dieksekusi sekali di ronde berikut |
| F-15 | Medium | Sinyal tanpa market data ditandai `DISPATCHED` padahal tak ada akun yang menilainya | `DISPATCHED` hanya setelah ada verdict; sisanya tetap `PENDING` lalu `EXPIRED` | e2e |
| F-19 | Medium | Token SPL baru default "authority revoked" padahal tidak ada pengecekan on-chain → gerbang keamanan token copy-trade lolos buta | Token SPL baru dibuat dengan kedua flag `False` (fail-closed) | 14 self-check hijau. **Baris token lama tidak diubah** |
| F-20 | High | Engine Rust membaca satu segmen TCP; httpx mengirim header & body terpisah → ±84% request nyata dijawab 400 → semua sinyal ditolak saat `ENGINE_URL` diisi | Baca request utuh sesuai `Content-Length` (maks 64 KB, timeout 5 dtk) | Probe client produksi: 42/50 HTTP 400 → 50/50 HTTP 200; cargo test regresi request terpisah |
| F-21 | Low | bcrypt 5.0 melempar error untuk password > 72 byte → register/login HTTP 500 | Validator 72 byte UTF-8 di kedua endpoint → 422 | `test_http` |
| F-22 | Medium | Kill switch menampilkan "LIVE LOCK ENGAGED" sebelum (dan terlepas dari) hasil API; Settings menampilkan "belum ada key" saat backend mati | Status engaged hanya bila sukses; error tampil sebagai `role="alert"` | Playwright (gagal pada versi lama) |
| F-23 | Low | Label ambang RiskGatePanel di-hardcode (salinan ketiga) | `/risk/status` mengirim `limits`; panel merendernya | Playwright + `test_http` |
| F-25 | Medium | Telegram `/status` membaca field per-akun yang tidak ada di `system_status()` → `KeyError` → bot tidak pernah membalas `/status` | Format ringkasan operator yang memang diterima; runbook & README diselaraskan | Reproduksi `KeyError` di image; `test_telegram_bot` + cek terhadap fungsi asli di `test_http` |

Dokumen ikut diselaraskan dengan perilaku nyata: README `/kill` **tidak** melikuidasi posisi (klaim lama keliru), smoke test README memakai `/health` (string log yang dirujuk tidak pernah ditulis kode), runbook Telegram kini menyebut `TELEGRAM_ALLOWED_CHAT_ID` wajib dan tidak lagi mengklaim upaya akses ditolak dicatat ke `system_events`.

---

## 4. Temuan baru — belum diperbaiki (butuh keputusan pemilik)

| ID | Sev. | Masalah | Kenapa belum dikerjakan |
|---|---|---|---|
| F-16 | High | *(Diperbarui di laporan 14: rantai intake → scoring → approval → sinyal kini berjalan; sisa: Risk Gate menolak sinyal SPL karena spread DEX tidak diketahui. Alasan "butuh sumber data baru" di kolom kanan keliru — `BLOCKCHAIN_DATA_SOURCES.md` §2 sudah memilih DEXScreener.)* **Copy-trade tidak bisa berjalan end-to-end:** tidak ada jalur yang membuat baris `wallets` (discovery); tidak ada API/UI approval `PENDING_REVIEW → APPROVED`; token SPL tidak pernah mendapat `pool_liquidity_usd` (copy-trade menolak < $20k) maupun `market_snapshots` (risk engine tak bisa menilai); harga swap dihitung dalam SOL, bukan USD | Butuh sumber data Solana baru (harga, likuiditas, otoritas token) dan desain UX discovery/approval — keputusan arsitektur & biaya API, bukan perbaikan lokal |
| F-17 | Medium | Pintu 6 wajib R:R ≥ 1:1.5 (FR baris 106) belum diterapkan | Perlu keputusan basis R:R (TP1 atau blend TP1/TP2); mengubah logika risiko → harus serentak di Python, Rust, dan kasus parity |
| F-18 | Medium | Eksekusi paper ditulis dengan beberapa commit terpisah; crash di tengah bisa meninggalkan state parsial (mis. RiskCheck lolos tanpa order). Guard F-13 mencegah duplikat, tetapi order yang terputus tidak dibuat ulang | Perubahan transaksi di jalur eksekusi inti — layak jadi perubahan tersendiri dengan test kegagalan |
| F-24 | Low | `npm audit`: postcss (high) lewat next 15.5.28; perbaikan menuntut Next 16 (major) | Upgrade major berisiko breaking; postcss hanya memproses CSS proyek saat build |
| GAP-23 | — | Belum ada CI; semua test hanya berjalan bila dijalankan manual | Perlu pilihan platform CI |

---

## 5. Hasil verifikasi (semua dijalankan pada sesi ini)

| Suite | Perintah | Hasil |
|---|---|---|
| Self-check backend (pure) | `python -m src.<modul>` ×14 di image backend | 14/14 `ok` |
| Rust engine | `cargo test` | 12/12 (termasuk request terpisah & request kebesaran) |
| Integrasi | `bash scripts/run_integration_tests.sh` | migrasi DB kosong (20 tabel), HTTP dev, HTTP prod (cookie Secure), e2e engine off/up/down, parity vs image engine — semua `ok`, 0 container tersisa |
| UI end-to-end | `cd frontend && npm run test:e2e` | 7/7 |
| Lint frontend | `npm run lint` | bersih |
| Latensi engine | 200 panggilan `call_risk_engine`, timeout produksi 10 ms | 200/200 lolos; p50 0,9 ms, p99 1,7 ms |

---

## 6. Berkas yang diubah/ditambah (sesi ini)

- **Backend:** `main.py`, `api/admin_routes.py`, `api/auth_routes.py`, `api/routes.py`, `risk/engine.py`, `ingestion/solana.py`, `control/telegram_bot.py`; test: `test_main.py` (baru), `api/test_http.py`, `risk/test_engine_e2e.py` (ditulis ulang), `risk/test_parity.py`, `control/test_telegram_bot.py`.
- **Engine:** `engine/src/main.rs` (framing HTTP + 2 test).
- **Frontend:** `KillSwitch.tsx`, `RiskGatePanel.tsx`, `app/settings/page.tsx`, `package.json`/`package-lock.json` (Playwright), `playwright.config.ts`, `e2e/` (baru), `.gitignore`.
- **Skrip:** `scripts/run_integration_tests.sh` (baru).
- **Konfigurasi & dokumen:** `.env.example`, `README.md`, `docs/02-architecture/AI_AGENT_ARCHITECTURE.md`, `RUST_ENGINE_INTEGRATION_SPEC.md`, `docs/04-data/DATA_DICTIONARY.md`, `docs/03-diagrams/ERD.mmd`, `docs/00-overview/OPEN_QUESTIONS.md`, `docs/05-security/TELEGRAM_BOT_SETUP_AND_RUNBOOK.md`, `docs/audit/REQUIREMENTS_TRACEABILITY_MATRIX.md`, plus 9 dokumen lain (hanya link).
- **Dibersihkan:** `backend/pos_check.py` dan `backend/wallet_wire_check.py` — file kosong yang tidak sengaja terbuat oleh bind-mount Docker pada sesi sebelumnya.

---

## 7. Yang belum diuji

- Loop background tidak dijalankan bersamaan dalam waktu lama (tidak ada soak/load test; stop conditions belum ditetapkan).
- Graceful shutdown hanya diverifikasi lewat kode, belum di bawah beban.
- Panggilan nyata ke OpenRouter/9Route, Binance, Solana RPC, dan Telegram — semua di-mock atau tidak dipanggil.
- Endpoint yang tetap `NOT_TESTED` di `03-api-inventory.csv` (pause, account/*, logout, admin PATCH) dan interaksi UI yang tetap `NOT_TESTED` di `02-ui-interaction-inventory.csv`.
- Konfigurasi Nginx/UFW di `deploy/` belum pernah diterapkan ke VPS.
