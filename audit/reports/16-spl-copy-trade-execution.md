# 16 — F-16: Model Spread/Fee DEX, Continuous Poller, & Crawler Otomatis

**Tanggal:** 2026-10-28
**Komponen:** `backend/src/ingestion/solana.py`, `backend/src/risk/gate.py`, `backend/src/risk/broker.py`, `backend/src/risk/engine.py`, `backend/src/config.py`, `backend/src/api/admin_routes.py`
**Status F-16:** **RESOLVED** (Selesai dan Terverifikasi)

---

## 1. Latar Belakang & Masalah (Root Cause)

Sebelumnya pada laporan audit 14, rantai intake wallet kandidat hingga pembuatan sinyal `TradingSignal(PENDING)` telah berhasil dibangun. Namun, eksekusi order paper copy-trade SPL terblokir 100% karena 4 faktor:
1. **Spread Pool DEX Tidak Diketahui (Fail-Closed):** Snapshot pool AMM dari DEXScreener tidak memiliki kuotasi bid/ask diskrit (`bid_price` dan `ask_price` bernilai `None`). Akibatnya, `_spread_or_fail` mengembalikan `UNKNOWN_SPREAD_PCT = 100%`, sehingga Risk Gate selalu menolak dengan alasan `SPREAD_OR_LIQUIDITY_INADEQUATE`.
2. **Ketiadaan Parameter Ambang Khusus DEX:** Ambang batas default Risk Gate dirancang ketat untuk Binance Spot (`max_spread_pct = 0.08%`, `min_volume = $1,000,000`). Pada DEX AMM seperti Raydium/Orca, biaya swap dasar pool (*base fee*) sendiri sudah berkisar 0.25%–0.30%, sehingga tidak mungkin lolos batas 0.08%.
3. **Ketiadaan Continuous Price Poller untuk Posisi SPL:** Pembaruan snapshot harga token SPL hanya terpanggil saat ada swap BUY segar dari wallet yang dipantau. Ketika bot berhasil membuka posisi SPL, harga posisi tersebut tidak pernah diperbarui lagi di background, sehingga pemantauan exit TP1/TP2/SL di `_monitor_positions` tidak pernah terpicu.
4. **Penemuan Wallet Kandidat Masih Manual:** Belum ada crawler otomatis untuk menjaring trader aktif dari program DEX Solana.

---

## 2. Implementasi yang Diterapkan

### A. Model Estimasi Spread & Fee AMM DEX (`_refresh_market`)
- Mengimplementasikan model kuotasi sintetis AMM berbasis kedalaman likuiditas:
  $$\text{half\_spread} = \text{dex\_pool\_base\_fee\_pct} (0.30\%) + \min\left(2.0\%, \frac{\$100}{\text{pool\_liquidity\_usd}}\right)$$
  $$\text{bid\_price} = \text{price} \times (1 - \text{half\_spread})$$
  $$\text{ask\_price} = \text{price} \times (1 + \text{half\_spread})$$
  $$\text{spread\_pct} = \frac{\text{ask\_price} - \text{bid\_price}}{\text{price}} \times 100$$
- Pool likuid ($500.000) menghasilkan spread $\approx 0.64\%$.
- Jika pool tidak memiliki likuiditas ($\le 0$), bid/ask tetap `None` sehingga tetap ditolak secara *fail-closed*.

### B. Venue-Aware Risk Gate Limits (`evaluate_risk` & `risk_limits`)
- Menambahkan konfigurasi di `config.py`:
  - `max_dex_spread_pct = 0.025` (maksimal spread 2.50% untuk pool DEX AMM).
  - `min_dex_24h_volume_usd = 20000.00` ($20.000, selaras dengan `MIN_POOL_LIQUIDITY_USD`).
  - `dex_pool_base_fee_pct = 0.0030` (0.30% taker fee pool).
- `evaluate_risk` dan `risk_limits(venue)` secara otomatis menerapkan batasan ini saat `venue == "SOLANA_DEX_SIM"`.
- Rust Risk Gate menerima limits ini melalui kontrak payload tunggal `_signal_candidate` (menjaga paritas Python↔Rust).
- Di `backend/src/risk/broker.py`, `fee_for_venue` kini membebankan fee transaksi DEX 0.30% + gas fee native 0.000005 SOL.

### C. Continuous Price Poller untuk Posisi SPL Terbuka (`refresh_open_spl_positions`)
- Fungsi `refresh_open_spl_positions(client, session)` memindai seluruh posisi `OPEN` atau `PARTIALLY_CLOSED` pada token berantai `solana`.
- Secara berkala mengambil harga terbaru dari DEXScreener dan menyimpan `MarketSnapshot` segar, sehingga `_monitor_positions` dapat mengeksekusi TP1 (tutup setengah & pindahkan stop ke breakeven), TP2, atau Stop Loss.
- Dipanggil otomatis pada setiap siklus `run_solana_ingestion` (interval 15 detik).

### D. Automated Wallet Discovery Crawler (`crawl_candidate_wallets`)
- Fungsi `crawl_candidate_wallets(client, session, limit)` memindai transaksi swap terbaru pada program DEX Solana utama (Raydium AMM V4 dan Jupiter Router v6).
- Mengekstrak signer/trader asli dari `accountKeys`, memfilter program ID bawaan sistem, memvalidasi format alamat Solana base58, dan mendaftarkan alamat baru ke tabel `wallets` dengan status `DISCOVERED` serta mencatat `SystemEvent(WALLET_DISCOVERED)`.
- Disediakan endpoint admin `POST /api/v1/admin/wallets/crawl` dan dipanggil otomatis di background loop setiap 20 siklus (~5 menit).

---

## 3. Hasil Pengujian & Bukti Runtime

1. **Unit Test Baru `backend/src/ingestion/test_solana_dex.py`:**
   - `test_amm_spread_model_liquid_pool`: Lolos ($500k liquidity -> spread 0.64%, bid < price < ask).
   - `test_amm_spread_model_zero_liquidity_fail_closed`: Lolos (0 liquidity -> bid/ask None, fail-closed).
   - `test_execution_venue_and_fees`: Lolos (DEX fee 0.30% + native gas).
   - `test_crawler_discovers_trader`: Lolos (transaksi Raydium diekstrak -> wallet `DISCOVERED`).
   - `test_refresh_open_spl_positions_calls_refresh_market`: Lolos (posisi terbuka diperbarui harganya).
2. **Pengujian Pintu Risiko `backend/src/risk/test_gate.py`:**
   - 16 test cases lulus `ok` (termasuk sinyal SPL valid lolos, spread > 2.5% ditolak, volume < $20k ditolak).
   - Paritas fee dan expectancy terverifikasi.
3. **Pengujian End-to-End Rantai Copy-Trade `backend/src/agents/test_copy_trade_chain.py`:**
   - Step 1–5: Intake -> scoring -> approval -> swap segar BUY terdeteksi.
   - Step 6: Evaluasi Risk Gate lolos -> `PaperOrder` dibuat dan `FILLED` -> `Position` dibuka pada token SPL (`SOLANA_DEX_SIM`).
   - Step 7: Poller harga SPL mendeteksi kenaikan harga ke $0.55 -> `_monitor_positions` mengeksekusi TP1 (tutup 50%, stop loss bergeser ke breakeven, status `PARTIALLY_CLOSED`).
   - Step 8: Crawler menemukan wallet kandidat baru -> status `DISCOVERED`.
   - Step 9: Endpoint `POST /api/v1/admin/wallets/crawl` terverifikasi merespons HTTP 200.
4. **Seluruh Self-Check Suite Backend:**
   - `test_gate`, `test_heuristics`, `test_copy_trade`, `test_wallet_scorer`, `test_anti_manipulation`, `test_solana_dex`, `test_ledger`, `test_aggregator`, `test_telegram_bot`, `test_burner_guard` semuanya lulus `ok`.

