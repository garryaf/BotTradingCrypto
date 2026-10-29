# 14 — P1-1 / GAP-02: Rantai Copy-Trade (discovery → scoring → approval → sinyal)

**Tanggal:** 2026-10-26
**Lingkup:** membuktikan dan memperbaiki rantai copy-trade secara utuh pada data synthetic. Solana RPC dan DEXScreener di-mock di lapisan HTTP (tidak ada panggilan jaringan saat test); DB Postgres sekali pakai; tanpa order live.

## 1. Keputusan desain — diambil dari dokumen repo, bukan dibuat baru
- **Approval wallet: manual oleh operator.** `WALLET_DISCOVERY_FLOWCHART.mmd` ("Human-in-the-Loop Approval") dan `DATA_MODEL.md` §3.1: `PENDING_REVIEW → ACTIVE_MONITORED` (setuju) atau `ARCHIVED` (tolak/berhenti pantau).
- **Sumber harga & likuiditas token SPL: DEXScreener** (`BLOCKCHAIN_DATA_SOURCES.md` §2). Koreksi atas laporan 13 §4, yang menyebut pilihan sumber data masih butuh keputusan pemilik — dokumen repo sudah memutuskannya.
- **SELL dari wallet master = exit, bukan entry** (`COPY_TRADING_FLOWCHART.mmd`, cabang SELL).

## 2. Titik putus yang ditemukan dan diperbaiki
| # | Masalah | Perbaikan |
|---|---|---|
| 1 | Tidak ada cara memasukkan wallet kandidat (tabel `wallets` hanya dibaca) | `POST /api/v1/admin/wallets` (admin, validasi alamat base58, 409 bila duplikat) |
| 2 | Tidak ada jalur approval | `PATCH /api/v1/admin/wallets/{address}` `{status: ACTIVE_MONITORED \| ARCHIVED}`; setuju hanya dari `PENDING_REVIEW` (409 bila tidak); tercatat di `system_events` |
| 3 | **F-28:** transaksi wallet yang lebih tua dari 30 detik dimasukkan DLQ dan tidak pernah dicatat → wallet baru tidak pernah bisa di-skor; signature yang sama di-DLQ lagi setiap polling 15 detik | Riwayat selalu dicatat untuk scoring; hanya swap yang masih segar yang boleh disalin; tidak ada lagi DLQ untuk riwayat |
| 4 | Precondition copy-trade mustahil terpenuhi: token SPL baru default tidak aman (F-19) dan `pool_liquidity_usd` tidak pernah diisi; harga sinyal = rasio SOL/token (atau $100 hardcoded) dipakai sebagai harga USD | Saat swap BUY segar: otoritas mint dibaca dari akun mint on-chain; harga USD, likuiditas, dan volume 24 jam dari DEXScreener disimpan sebagai `market_snapshots` |
| 5 | Wallet `ARCHIVED` tetap di-polling | `POLLED_WALLETS` mengecualikan `ARCHIVED` |
| 6 | **F-27 (sisi copy-trade):** swap SELL master dijadikan sinyal entry SELL, yang dibuka broker spot sebagai posisi **long** | Copy-trade menolak SELL (`SELL_NOT_MIRRORED`); posisi kita keluar lewat SL/TP sendiri |
| 7 | Snapshot pool DEX tidak punya bid/ask; engine memetakan spread yang tak diketahui menjadi 0 → gerbang spread lolos | Spread dianggap tidak diketahui bila bid/ask kosong → gerbang spread gagal (fail-closed), di Python dan di payload Rust |

**Catatan penting untuk butir 7:** perbaikan pertama saya hanya memeriksa `spread_pct is None`. Test rantai menangkap bahwa itu **tidak bekerja**: kolom `spread_pct` punya `server_default 0.0000`, sehingga nilai kosong tersimpan sebagai 0 dan sinyal copy-trade SPL **lolos semua gerbang** (akan membuka paper order dengan spread 0 dan fee DEX 0). Perbaikan akhir memakai ketiadaan bid/ask sebagai penanda, dan test kini juga memastikan tidak ada paper order.

## 3. Bug lain yang ditemukan saat verifikasi
| ID | Sev. | Masalah | Status |
|---|---|---|---|
| F-26 | High | `_monitor_positions` menulis `paper_order_id = position.id` untuk fill exit → melanggar FK `paper_trades → paper_orders` pada **setiap** TP1/TP2/SL → tidak ada posisi yang pernah tertutup, snapshot akun tidak diperbarui (circuit breaker drawdown tidak melihat kerugian itu), dan akun berikutnya dalam putaran yang sama ikut terlewat. Berlaku juga untuk posisi BUY biasa | **Diperbaiki**: fill exit dibukukan pada order pembuka posisi (skema `paper_orders.risk_check_id NOT NULL` tidak memungkinkan order exit tersendiri). Test regresi gagal sebelum perbaikan (FK violation) dan lulus sesudahnya |
| F-27 | High | Sinyal SELL (dari Hermes) dieksekusi sebagai posisi long di broker spot | Sisi copy-trade diperbaiki (butir 6). **Sisi Hermes terbuka** — butuh keputusan (lihat §5) |
| F-29 | Medium | Max drawdown wallet di skor selalu 0: dihitung dari jumlah nilai trade (selalu naik), dan `price_usd` observasi tidak pernah diisi → komponen drawdown selalu memberi +30 poin ke skor komposit | **Terbuka** — perubahan model scoring (butuh keputusan basis PnL & drawdown) |
| — | Low | Kolom harga `NUMERIC(18,6)` tidak bisa menyimpan token dengan harga < ~$0,001 secara presisi → SL sama dengan entry → sinyal ditolak Risk Gate (fail-closed, tidak berbahaya) | **Terbuka** — butuh migrasi presisi |

## 4. Bukti

**Test baru `backend/src/agents/test_copy_trade_chain.py`** (dijalankan oleh `scripts/run_integration_tests.sh`, DB kosong, RPC & DEXScreener di-mock):
1. Intake: alamat tidak valid → 422; dua wallet ditambahkan → `DISCOVERED`; duplikat → 409; approval sebelum scoring → 409.
2. Ingestion: 8 transaksi riwayat (berjam-jam lalu) tercatat sebagai observasi; polling ulang tidak menggandakan; **0 entri DLQ**; **0 sinyal**; **0 panggilan** DEXScreener/`getAccountInfo` untuk riwayat.
3. Scoring: wallet untung → `PENDING_REVIEW` (skor ≥ 70); wallet rugi tetap `DISCOVERED` (skor < 70).
4. Approval: `PATCH` → `ACTIVE_MONITORED` + `approved_at` + `system_events WALLET_APPROVED`; wallet lemah tidak bisa disetujui (409).
5. Swap segar dari wallet yang disetujui: BUY token aman → **tepat 1 `TradingSignal` BUY `PENDING`** dengan harga entry **$0,50 (USD dari DEXScreener)**, flag otoritas token terverifikasi, likuiditas $500.000 tersimpan. SELL → `SELL_NOT_MIRRORED`; BUY token dengan freeze authority aktif → `TOKEN_UNSAFE_AUTHORITY_NOT_REVOKED`.
6. Risk engine: sinyal SPL ditolak dengan tepat satu alasan `SPREAD_OR_LIQUIDITY_INADEQUATE`; **tidak ada paper order**.
7. Arsip: wallet `ARCHIVED` tidak lagi masuk daftar polling.

**F-26 (exit posisi):** blok baru di `test_engine_e2e.py` (posisi BUY biasa: harga 111 → TP1 tutup setengah, stop ke breakeven; harga 94 → SL tutup sisa; PnL terealisasi positif; snapshot akun: nilai posisi 0, kas > modal awal). Sebelum perbaikan test ini **gagal** dengan `paper_trades_paper_order_id_fkey`; sesudahnya lulus.

**Hasil run:**
| Suite | Hasil |
|---|---|
| `bash scripts/run_integration_tests.sh` (run 2) | 8/8 `ok`: migrasi DB kosong (20 tabel), HTTP dev, HTTP prod, e2e engine off (termasuk F-26) / up / down, rantai copy-trade, parity vs image engine |
| Run 1 (sebelum perbaikan butir 7) | 7/8; rantai copy-trade **gagal**: sinyal SPL lolos semua gerbang (`rejection_reasons == []`) |
| `cd frontend && npm run test:e2e` | 9/9 (2 test baru: approval + refresh daftar, intake + error duplikat; tombol keputusan tersembunyi untuk non-admin) |
| `npm run lint` | bersih |
| 14 self-check backend (`python -m src.<modul>`) | 14/14 `ok` (termasuk test baru `SELL_NOT_MIRRORED`) |
| `cargo test` (engine tidak diubah) | 12/12 |

**Probe F-29** (fungsi murni `calculate_wallet_metrics`, deret: rugi, rugi, untung):
```
price_usd=0 (yang ditulis solana.py): trades=3 win%=33.33 PF=1.25 MDD%=0.00 score=56.25
price_usd=1 (seandainya harga diisi):  trades=3 win%=33.33 PF=1.25 MDD%=0.00 score=56.25
```
Dua kerugian beruntun tetap menghasilkan drawdown 0%, sehingga komponen drawdown selalu memberi nilai penuh.

**Probe F-27** (sinyal SELL langsung ke risk engine yang sudah diperbaiki, harga tetap 100):
```
risk gate passed: True
opened:     status=OPEN             qty=10.0000 entry=99.95 realized= 0.00 cash=8999.50  (dari 10000)
monitor #1: status=PARTIALLY_CLOSED qty= 5.0000              realized=-0.25 cash=9499.00
monitor #2: status=CLOSED           qty= 0.0000              realized=-0.50 cash=9998.50
```
Sinyal SELL membuka posisi **long**, lalu dalam dua putaran monitor (±10 detik) "take profit" palsu menutupnya (TP untuk SELL berada di bawah entry), dengan kerugian $1,50 dari fee dan spread. Copy-trade tidak lagi membuat sinyal seperti ini; Hermes masih bisa.

## 5. Yang masih terbuka (butuh keputusan pemilik)
1. **Model spread/fee DEX** — tanpa ini Risk Gate menolak semua sinyal copy-trade SPL. Opsi: estimasi spread dari fee pool + price impact berdasarkan likuiditas; atau gerbang terpisah untuk venue DEX.
2. **Hermes SELL (F-27)** — opsi: (a) Hermes membuang sinyal SELL, (b) SELL = tutup posisi long yang ada, (c) dukung short (bukan spot).
3. **Scoring drawdown (F-29)** dan basis PnL (SOL vs USD).
4. Dilewati dengan sengaja: pencarian kandidat otomatis (leaderboard/swap besar), backfill riwayat 30 hari, notifikasi Telegram saat wallet dipromosikan, un-archive, menutup posisi kita saat master SELL.
