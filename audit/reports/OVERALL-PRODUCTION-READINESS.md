# PENILAIAN KESIAPAN PRODUKSI — BOTTRADINGCRYPTO

**Tanggal:** 2026-10-26 · **Basis:** hasil Discovery + `OVERALL-APPLICATION-AUDIT-ID.md`. **Belum ada pengujian runtime** pada fase ini.

## Pembaruan setelah remediasi (2026-10-26, berbasis test runtime)

Bagian di bawah judul ini menggantikan verdict lama; bagian berikutnya dibiarkan sebagai baseline.

| Tahap | Verdict | Alasan |
|---|---|---|
| A. Development | **Ready** | Image backend & engine build bersih; `next build` bersih; migrasi diverifikasi di DB kosong |
| B. Functional testing | **Ready** | 4 suite dapat dijalankan satu perintah dan hijau: 14 self-check, cargo 12, integrasi 7, Playwright 7 |
| C. Staging | **Ready with conditions** | Semua prasyarat staging lama terpenuhi (F-02/F-03/F-04 tutup, e2e + migrasi terbukti, monitoring dasar, build bersih). Copy-trade SPL kini terbukti membuka posisi paper order dan exit TP/SL (F-16 selesai). Syarat tersisa: belum ada CI (GAP-23), resource limits belum diset, backup/restore belum diuji. |
| D. Production | **Not ready** | Soak 30 hari (Fase 6) belum dijalankan; F-18 terbuka; tidak ada CI, alerting, rollback, atau resource limits; advisory npm (F-24) |

Checklist yang berubah:

| Item | Lama | Baru | Bukti |
|---|---|---|---|
| Clean build | Not assessed | Ready | `docker build` backend & engine; `next build` |
| Database migration | Not assessed | Ready | 001→005 pada DB kosong → 20 tabel domain |
| Health checks | Ready with conditions | Ready with conditions | `/health` kini melaporkan status loop + `degraded`; compose belum punya healthcheck backend |
| Monitoring | Not ready | Ready with conditions | `/api/v1/admin/metrics` + status loop; belum ada alerting/stack terpusat |
| Risk Gate behavior | Not assessed | Ready | parity Python↔Rust (image), e2e engine off/up/down, idempoten, loop tahan error DB; spread tak diketahui (pool DEX) = gagal |
| Exit posisi (TP1/TP2/SL) | (tidak dinilai) | Ready | Sebelumnya tidak pernah tereksekusi (F-26); kini terbukti e2e: TP1 → stop breakeven → SL menutup posisi dan memperbarui snapshot |
| Trading kill switch | Ready with conditions | Ready | API `< 2 dtk` + UI tidak lagi melaporkan "engaged" palsu |
| Graceful shutdown | Ready with conditions | Ready with conditions | cancel + await; belum diuji di bawah beban |
| Nginx & UFW | Not assessed | Ready with conditions | Artefak di `deploy/`; belum diterapkan ke VPS |
| CI/CD | Not ready | Not ready | Belum ada pipeline (GAP-23) |
| Dependency pinning | Ready with conditions | Ready with conditions | Frontend di-pin; advisory npm F-24 |

## Verdict per tahap

| Tahap | Verdict | Alasan singkat (berbasis bukti) |
|---|---|---|
| A. Development | **Ready with conditions** | Compose dev + Dockerfile ada; perlu `.env` terisi. Build bersih belum dibuktikan. |
| B. Functional testing | **Ready with conditions** | Self-check backend + `cargo test` tersedia; butuh Docker + Postgres disposable. Tanpa API key untuk self-check (per README). |
| C. Staging | **Not ready** | Nol bukti runtime; F-02/F-03/F-04 terbuka; migration belum diuji di DB bersih. |
| D. Production | **Not ready** | Selain poin staging: tidak ada monitoring/CI-CD/rollback/resource limits; soak Fase 6 masih berjalan; Fase 7 (live) terkunci struktural (sengaja). |

> Skala verdict: **Ready / Ready with conditions / Not ready / Not assessed** (tidak cukup bukti untuk menilai).

## Checklist terperinci

| Item | Verdict | Bukti / catatan |
|---|---|---|
| Clean build (backend & frontend) | Not assessed | `pip install -e .` & `npm run build` belum dijalankan fase ini |
| Database migration apply | Not assessed | rantai 001→005 ada; belum diuji pada DB bersih |
| Konfigurasi environment | Ready with conditions | `.env.example` lengkap; **3 default model AI berbeda** (GAP-18) |
| Secrets handling | Ready with conditions | Fernet field-encryption + bcrypt + JWT; **cookie belum `secure`** (F-04); startup menolak jika JWT/Fernet key kosong |
| Health checks | Ready with conditions | `/api/v1/health` + healthcheck Postgres ada; **backend tak punya healthcheck di compose** |
| Startup dependencies / ordering | Ready | prod: `depends_on: postgres service_healthy` |
| Database readiness | Ready with conditions | menunggu Postgres healthy; apply migration via CMD Dockerfile |
| Logging | Ready with conditions | modul `logging` dipakai; belum terstruktur/terpusat |
| Monitoring | Not ready | tidak ada metrik/monitoring (GAP-14) |
| Backup & restore | Ready with conditions | skrip backup (README) + `scripts/drill_db_restore.sh`; **belum diuji** |
| Rollback | Not ready | tidak ada strategi rollback eksplisit |
| Container configuration | Ready with conditions | prod bind `127.0.0.1`, `restart: always`, named volume, network terisolasi, user non-root (frontend) |
| Resource limits | Not ready | tidak diset di compose |
| Dependency pinning | Ready with conditions | backend pakai `>=` (bukan pin ketat); **versi frontend mencurigakan** (GAP-17) |
| Network exposure | Ready (prod) | prod bind localhost; **dev compose publish 5432/8000/3000 ke semua interface** (hanya untuk dev) |
| **Nginx reverse proxy** | **Not assessed** | **tidak ada konfig di repo (F-11); mungkin dikonfigurasi di host di luar repo — tidak disimpulkan "belum diimplementasikan"** |
| **UFW firewall** | **Not assessed** | idem — hanya prosa README |
| TLS / SSL | Not assessed | via Certbot di host (README), di luar repo |
| CI/CD | Not ready | tidak ada pipeline |
| Graceful shutdown | Ready with conditions | hanya `task.cancel()`; perlu uji drain (GAP-16) |
| Risk Gate behavior | Not assessed | F-02 terbuka; belum diuji runtime |
| Trading kill switch | Ready with conditions | kode `/kill` sinkron (target <2s); belum diuji runtime |
| Exchange order reconciliation | Not applicable | paper mode; tidak ada order exchange nyata |
| Live trading lock | Ready | terkunci rangkap 3 di startup (`assert_paper_mode`, cek `live_trading_enabled`, tidak ada kode order live) |
| Operational runbook | Ready with conditions | README + `docs/05-security/*` (SOP circuit breaker, Telegram runbook, safety gate) lengkap |

## Konfirmasi keselamatan positif (dari kode, [A])
- Tidak ada jalur LLM→order langsung; eksekusi hanya setelah Risk Gate lolos.
- Live trading terkunci struktural; tidak ada kode eksekusi dana riil.
- Kredensial tidak di-log; Binance key hanya muncul sebagai last-4.
- `engine_client` fail-closed pada timeout/error/respons invalid.
- `/kill` membatalkan sinyal PENDING secara sinkron.

## Catatan Nginx/UFW (sesuai arahan)
Konfigurasi Nginx & UFW **tidak ditemukan sebagai artefak di repository**. Ini **tidak** sama dengan "belum diimplementasikan": keduanya lazim dikonfigurasi langsung di host VPS (sesuai panduan README Opsi 2). Verdict keduanya **Not assessed** sampai dikonfirmasi apakah ada konfigurasi aktif di host target. Rekomendasi (P3): bila belum ada di host, commit konfig sebagai artefak `deploy/` agar deployment reproducible.

## Prasyarat menuju staging (ringkas)
Tutup F-02, F-03, F-04; buktikan Risk Engine e2e + migration di DB disposable; tambahkan monitoring dasar; konfirmasi build bersih. Detail & urutan di `OVERALL-REMEDIATION-ROADMAP.md`.
