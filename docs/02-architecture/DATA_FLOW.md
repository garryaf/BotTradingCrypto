# ALIRAN DATA SISTEM (DATA FLOW)
**Dokumen:** `docs/02-architecture/DATA_FLOW.md`  
**Proyek:** AI Crypto Trading & Copy-Trading Platform (AUTO-TRADE-AA)  
**Versi:** 1.0.0 (Tahap 0)  
**Status:** Draf Resmi Arsitektur  

---

Dokumen ini memetakan siklus hidup dan aliran data lengkap (*end-to-end data lifecycle*) mulai dari penarikan data transaksi on-chain di jaringan Solana hingga pembaruan metrik pada antarmuka pengguna dan notifikasi Telegram.

---

## 1. Diagram Aliran Data Utama (End-to-End Data Pipeline)

```
[ Solana RPC / WebSocket / DEX API ]
                │
                ▼ (1. Raw Ingestion)
[ Ingestion & Normalizer Pipeline ] ──► (2. Deduplikasi Signature)
                │
                ▼ (3. Simpan Raw Observations)
      [(DB) wallet_observations]
                │
                ▼ (4. Trigger Event Swap)
[ Hermes Multi-Agent Orchestrator ]
    ├──► Token Safety Agent ──► AI Model Gateway (OpenRouter / 9Route)
    ├──► Market Context Agent ──► Snapshot Likuiditas & Volume
    └──► Strategy Signal Agent ──► Sintesis Sinyal Terstruktur
                │
                ▼ (5. Validasi Skema JSON Sinyal)
      [(DB) trading_signals]
                │
                ▼ (6. Evaluasi Kebijakan Keselamatan)
    [ Deterministic Risk Engine ]
         ├──► Jika GAGAL: Simpan `risk_checks` (REJECTED) ──► Kirim Alert Telegram
         └──► Jika LOLOS: Simpan `risk_checks` (PASSED)
                │
                ▼ (7. Order Virtual Dispatch)
    [ Paper Broker Execution Simulator ]
         ├──► Hitung Estimasi Slippage Pasar
         ├──► Bebankan Biaya Gas & Protokol Simulasi
         └──► Cocokkan Order Virtual (Fill)
                │
                ▼ (8. Persistensi Transaksi & Pembukuan)
      [(DB) paper_orders & paper_trades]
                │
                ▼ (9. Rekonsiliasi Posisi & PnL FIFO)
      [(DB) positions & portfolio_snapshots]
                │
                ▼ (10. Diseminasi & Notifikasi)
    ┌───────────┴───────────────────────────┐
    ▼                                       ▼
[ Web Dashboard REST API ]       [ Telegram Bot Notification ]
 (Next.js Revalidation/Query)     (Alert Eksekusi / Ringkasan PnL)
```

---

## 2. Rincian Tahapan Aliran Data

### Tahap 1: Ingestion & Polling Mentah (Raw Ingestion)
- **Sumber Data:** Node Solana RPC (`getSignaturesForAddress`, `getTransaction`) atau Helius Enhanced Transaction Webhook.
- **Payload Input:** JSON mentah blok atau transaksi Solana Base58.
- **Tindakan:** Mengurai instruksi program DEX (Raydium AMM / Orca Whirlpool), mengekstrak mint address token masuk/keluar, jumlah token (*token amount*), nilai SOL, dan timestamp block time.

### Tahap 2: Deduplikasi & Normalisasi Data
- **Pemeriksaan Unik:** Signature transaksi diperiksa terhadap indeks unik di basis data. Jika signature sudah ada, transaksi langsung dibuang tanpa pemrosesan lanjutan (*idempotency*).
- **Normalisasi:** Data diubah ke format standar internal `NormalizedSwapEvent`:
  ```json
  {
    "wallet_address": "8x2...k9P",
    "tx_signature": "5UN...7yZ",
    "timestamp": 1776150600,
    "dex_protocol": "RAYDIUM",
    "action": "BUY",
    "token_mint": "DezXAZ8z7PnrnRJjz3wXBoRgixCa6xjnB7YaB1pPB263",
    "token_symbol": "BONK",
    "amount_token": 1500000.0,
    "amount_sol": 1.25,
    "price_per_token_sol": 0.000000833,
    "network_fee_sol": 0.000005
  }
  ```

### Tahap 3: Persistensi Observasi Wallet
- Record baru dimasukkan ke tabel `wallet_observations` dengan status `PARSED_SWAP`. Transaksi non-swap dicatat dengan status `IGNORED_TRANSFER`.

### Tahap 4: Orkestrasi Analisis Multi-Agent (Hermes)
- Jika wallet berstatus `ACTIVE_MONITORED` melakukan swap, Hermes Orchestrator memicu alur analisis terdistribusi:
  1. **Token Safety Agent:** Mengambil metadata token on-chain (apakah mint/freeze authority aktif, kepemilikan top 10 holders). Mengirimkan prompt analisis ke AI Model Gateway.
  2. **Market Context Agent:** Mengambil snapshot likuiditas pool DEX terkini untuk menghitung kedalaman likuiditas dan volatilitas 1 jam terakhir.
  3. **Strategy Signal Agent:** Mengombinasikan data copy-trade dan hasil analisa agen spesialis menjadi rekomendasi sinyal terstruktur.

### Tahap 5: Sintesis Sinyal Perdagangan Terstruktur
- Model AI menghasilkan objek JSON terstruktur yang divalidasi dengan skema Pydantic ketat:
  ```json
  {
    "strategy_id": "copy_trade_mirror_v1",
    "token_mint": "DezXAZ8z7PnrnRJjz3wXBoRgixCa6xjnB7YaB1pPB263",
    "action": "BUY",
    "target_price_sol": 0.000000835,
    "recommended_allocation_pct": 0.05,
    "confidence_score": 0.88,
    "rationale": "High-performing wallet accumulated 1.25 SOL; pool liquidity deep ($150k), mint authority revoked."
  }
  ```
- Sinyal disimpan ke tabel `trading_signals` dengan status `PENDING_RISK_CHECK`.

### Tahap 6: Evaluasi Deterministic Risk Gate
- Risk Engine memproses sinyal secara berurutan:
  - Cek usia data pasar (< 30 detik).
  - Cek likuiditas pool (harus ≥ $20.000 USD).
  - Cek persentase alokasi (harus ≤ 10% ekuitas portofolio).
  - Cek batas kerugian harian portofolio (harus < 15%).
- **Hasil Evaluasi:** Disimpan di tabel `risk_checks`.
  - Jika **GAGAL**: Sinyal ditandai `REJECTED`, alur eksekusi dihentikan, dan peringatan dikirim ke Telegram.
  - Jika **LOLOS**: Sinyal ditandai `PASSED` dan diteruskan ke Paper Broker.

### Tahap 7: Eksekusi Paper Broker Simulator
- Paper Broker membuat record `paper_orders` dengan status `SUBMITTED`.
- Menghitung *slippage* simulasi: $\text{Slippage} = \text{Order Size} / (\text{Pool Liquidity} \times 2)$.
- Menghitung harga eksekusi bersih (*effective fill price*).
- Menghasilkan record `paper_trades` dengan status `FILLED`.

> [!IMPORTANT]
> **[FIX 3.3] Model Partial Fill Paper Broker — Spesifikasi Eksplisit (Konservatif):**
>
> Model partial fill wajib menggunakan asumsi **konservatif** (tidak optimis) agar 30 hari paper trading sebagai syarat Fase 7 tidak memberikan *false confidence*. Berikut spesifikasi lengkapnya:
>
> | Parameter | Model yang Digunakan | Rasional |
> |---|---|---|
> | **Fill Ratio** | Proporsional terhadap kedalaman orderbook: `fill_ratio = min(1.0, orderbook_depth_at_price / order_size)`. Bukan selalu 100% fill. | Mencerminkan kenyataan bahwa order besar di pool kecil tidak selalu terisi penuh. |
> | **Fill Price** | Harga *mid-point* bid-ask + slippage penuh (bukan harga terbaik / best ask). Formula: `fill_price = mid_price × (1 + slippage_pct)` untuk BUY. | Asumsi optimis (fill di best bid/ask) akan melebih-estimasi profitabilitas. |
> | **Slippage Model** | AMM Price Impact: `slippage_pct = order_size_usd / (pool_liquidity_usd × 2)`. Minimum slippage = 0.05% (floor). | Floor mencegah slippage nol pada order kecil yang tidak realistis. |
> | **Fee Model** | Bybit Spot Taker Fee: **0.10%** per sisi (entry + exit = 0.20% round-trip). Solana DEX: Gas fee 0.000005 SOL per transaksi + protocol fee 0.25%. | Menggunakan taker fee (bukan maker) karena paper order diasumsikan market order. |
> | **Partial Fill Scenario** | Jika `fill_ratio < 1.0`: order tercatat sebagai `PARTIALLY_FILLED` dengan `filled_qty = order_qty × fill_ratio`. Sisa kuantitas (`remaining_qty`) di-*expire* setelah 60 detik (tidak di-queue). | Menghindari akumulasi order stale yang menipu statistik fill rate. |
> | **Rejection Scenario** | Jika `pool_liquidity_usd < order_size_usd × 10` (order > 10% pool): order langsung `REJECTED_INSUFFICIENT_LIQUIDITY` tanpa eksekusi. | Mencegah paper order yang mustahil dieksekusi di kondisi nyata. |
> | **Timestamp Lag** | Tambahkan simulated latency 50–500ms (uniform random) ke setiap fill untuk mensimulasikan network delay. | Strategi latency-sensitive (scalping) yang tampak profitable di paper bisa gagal di live karena latency. |
>
> **Konfigurasi model** disimpan di `config/paper_broker_config.yaml` dan dapat di-audit sebelum Fase 7. Setiap perubahan parameter model wajib dicatat sebagai ADR (*Architecture Decision Record*).

### Tahap 8 & 9: Akuntansi Posisi & Portofolio
- Saldo kas virtual diperbarui (dikurangi nilai pembelian + biaya simulasi).
- Kuantitas token virtual ditambahkan ke portofolio.
- Record posisi di tabel `positions` diperbarui atau dibuat baru.
- Snapshot ekuitas berkala disimpan di `portfolio_snapshots`.

### Tahap 10: Diseminasi Informasi
- **Web Dashboard:** Membaca data terbaru dari database PostgreSQL melalui endpoint REST API.
- **Telegram Bot:** Mengirim pesan ringkas terformat kepada operator melalui obrolan terotentikasi.
