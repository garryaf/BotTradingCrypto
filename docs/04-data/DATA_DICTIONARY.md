# KAMUS DATA LENGKAP (DATA DICTIONARY)
**Dokumen:** `docs/04-data/DATA_DICTIONARY.md`  
**Proyek:** AI Crypto Trading & Copy-Trading Platform (AUTO-TRADE-AA)  
**Versi:** 1.2.0 (akun & multi-user, sinkron dengan migrasi 005 — audit 2026-10-26)  
**Status:** Draf Resmi Basis Data  

---

Dokumen ini mendefinisikan rincian kamus data struktural untuk seluruh tabel basis data **PostgreSQL 16** pada platform **AUTO-TRADE-AA**.

> **Jumlah tabel (diverifikasi audit 2026-10-26 pada DB kosong, migrasi 001→005):** 20 tabel domain (= `backend/src/models.py`) + `alembic_version` = 21. Sampai versi 1.1.0 dokumen ini hanya memuat 18 tabel; `users` dan `binance_credentials` (migrasi 004/005) ditambahkan di Seksi 0.

---

## 0. Tabel: `users` & `binance_credentials` (migrasi `004`, `005`)
Akun dashboard dan kredensial Binance per akun. Setiap akun punya portofolio paper sendiri.

### Tabel `users`
| Kolom | Tipe Data | Nullable | Default | Deskripsi | Contoh Nilai |
|---|---|---|---|---|---|
| `id` | `UUID` | **NO** | — (dibuat aplikasi) | Primary Key akun. | `a1eebc99-9c0b...` |
| `email` | `VARCHAR(255)` | **NO** | — | Email login. **UNIQUE**, terindeks. | `'trader@example.com'` |
| `password_hash` | `VARCHAR(255)` | **NO** | — | Hash bcrypt; password maks. 72 byte, min. 8 karakter saat daftar. | `'$2b$12$...'` |
| `role` | `VARCHAR(16)` | **NO** | `'user'` | `user` / `admin`. User pertama yang mendaftar menjadi `admin` (migrasi 005). | `'admin'` |
| `is_active` | `BOOLEAN` | **NO** | `TRUE` | `FALSE` = akun dinonaktifkan admin; login ditolak (403). | `TRUE` |
| `created_at` | `TIMESTAMPTZ` | **NO** | `now()` | Waktu pendaftaran. | `2026-10-26 09:00:00+07` |
| `updated_at` | `TIMESTAMPTZ` | **NO** | `now()` | Waktu perubahan terakhir. | `2026-10-26 09:00:00+07` |

### Tabel `binance_credentials`
| Kolom | Tipe Data | Nullable | Default | Deskripsi | Contoh Nilai |
|---|---|---|---|---|---|
| `id` | `UUID` | **NO** | — (dibuat aplikasi) | Primary Key. | `b2eebc99-9c0b...` |
| `user_id` | `UUID` | **NO** | — | Foreign Key ke `users(id)`. **UNIQUE** — satu akun Binance per user. Akun tanpa baris ini tidak menerima sinyal dari Risk Engine. | `a1eebc99...` |
| `api_key_encrypted` | `TEXT` | **NO** | — | API key terenkripsi Fernet (`FIELD_ENCRYPTION_KEY`). Hanya 4 digit terakhir yang pernah ditampilkan. | `'gAAAAAB...'` |
| `api_secret_encrypted` | `TEXT` | **NO** | — | API secret terenkripsi Fernet. Tidak pernah dikembalikan API. | `'gAAAAAB...'` |
| `created_at` | `TIMESTAMPTZ` | **NO** | `now()` | Waktu disimpan. | `2026-10-26 09:05:00+07` |
| `updated_at` | `TIMESTAMPTZ` | **NO** | `now()` | Waktu diganti. | `2026-10-26 09:05:00+07` |

Migrasi 004 juga menambah `user_id UUID NOT NULL → users(id)` (terindeks) ke `positions`, `portfolio_snapshots`, dan `risk_checks`.

---

## 1. Tabel: `wallets`
Menyimpan data dompet on-chain Solana dan akun trader Binance yang diobservasi atau dipantau.

| Kolom | Tipe Data | Nullable | Default | Deskripsi & Aturan Bisnis | Contoh Nilai |
|---|---|---|---|---|---|
| `id` | `UUID` | **NO** | `gen_random_uuid()` | Primary Key unik internal sistem. | `a0eebc99-9c0b-4ef8-bb6d-6bb9bd380a11` |
| `address` | `VARCHAR(128)` | **NO** | — | Alamat publik on-chain Solana (Base58) atau Tag Akun Binance. **UNIQUE**. | `8x2M...P9kQ` |
| `chain` | `VARCHAR(32)` | **NO** | `'solana'` | Nama jaringan blockchain atau bursa (`solana`, `binance_spot`, `bybit_spot` [roadmap]). | `'solana'` |
| `label` | `VARCHAR(64)` | YES | `NULL` | Nama alias yang diberikan pengguna untuk mempermudah identifikasi. | `'Smart Whale #1'` |
| `status` | `VARCHAR(32)` | **NO** | `'DISCOVERED'` | Status dompet (`DISCOVERED`, `PENDING_REVIEW`, `ACTIVE_MONITORED`, `ARCHIVED`). | `'ACTIVE_MONITORED'` |
| `composite_score` | `NUMERIC(5,2)` | YES | `0.00` | Skor performa historis (0.00 s.d. 100.00). | `78.50` |
| `net_pnl_usd` | `NUMERIC(16,4)` | YES | `0.0000` | Akumulasi PnL terealisasi bersih historis, **dalam SOL** (dihitung dari delta saldo SOL, sudah bersih gas & fee pool). Nama kolom historis, dipertahankan agar tidak perlu migrasi. | `12.3400` |
| `win_rate_pct` | `NUMERIC(5,2)` | YES | `0.00` | Persentase kemenangan historis trader. | `62.50` |
| `profit_factor` | `NUMERIC(6,2)` | YES | `0.00` | Rasio total profit terhadap total loss. | `2.15` |
| `max_drawdown_pct`| `NUMERIC(5,2)` | YES | `0.00` | Maximum drawdown historis trader dari high-water mark ekuitas terealisasi; modal = SOL minimum yang mampu mendanai trade yang teramati. | `14.20` |
| `last_active_at` | `TIMESTAMPTZ` | YES | `NULL` | Waktu transaksi terakhir terdeteksi di on-chain. | `2026-10-14 14:30:00+07` |
| `approved_at` | `TIMESTAMPTZ` | YES | `NULL` | Waktu persetujuan operator untuk pemantauan aktif. | `2026-10-14 14:35:00+07` |
| `created_at` | `TIMESTAMPTZ` | **NO** | `CURRENT_TIMESTAMP` | Waktu data pertama kali dicatat. | `2026-10-14 14:00:00+07` |
| `updated_at` | `TIMESTAMPTZ` | **NO** | `CURRENT_TIMESTAMP` | Waktu pembaruan data terakhir. | `2026-10-14 14:35:00+07` |

---

## 2. Tabel: `wallet_observations`
Mencatat seluruh transaksi on-chain yang dilakukan oleh wallet yang dipantau.

| Kolom | Tipe Data | Nullable | Default | Deskripsi & Aturan Bisnis | Contoh Nilai |
|---|---|---|---|---|---|
| `id` | `UUID` | **NO** | `gen_random_uuid()` | Primary Key unik. | `b1eebc99-9c0b-4ef8-bb6d-6bb9bd380b22` |
| `wallet_id` | `UUID` | **NO** | — | Foreign Key ke tabel `wallets(id)`. | `a0eebc99...` |
| `tx_signature` | `VARCHAR(128)` | **NO** | — | Signature transaksi Base58 Solana / Order ID Binance. **UNIQUE**. | `5UN...7yZ` |
| `chain` | `VARCHAR(32)` | **NO** | `'solana'` | Jaringan asal transaksi. | `'solana'` |
| `dex_protocol` | `VARCHAR(32)` | YES | `NULL` | Protokol DEX atau bursa CEX (`RAYDIUM`, `ORCA`, `JUPITER`, `BINANCE`, `BYBIT`). | `'RAYDIUM'` |
| `action` | `VARCHAR(32)` | **NO** | — | Jenis aksi: `BUY`, `SELL`, `TRANSFER_IN`, `TRANSFER_OUT`, `LP_ADD`, `LP_REMOVE`. | `'BUY'` |
| `token_in_id` | `UUID` | YES | `NULL` | Foreign Key ke `tokens(id)` untuk token yang diserahkan. | `c2eebc99...` |
| `token_out_id` | `UUID` | YES | `NULL` | Foreign Key ke `tokens(id)` untuk token yang diterima. | `d3eebc99...` |
| `amount_in` | `NUMERIC(24,8)` | YES | `0` | Kuantitas token yang diserahkan. | `1.50000000` |
| `amount_out` | `NUMERIC(24,8)` | YES | `0` | Kuantitas token yang diterima. | `150000.00000000` |
| `price_usd` | `NUMERIC(18,6)` | YES | `0` | Harga satuan token saat swap setara USD. | `0.000012` |
| `network_fee_native`| `NUMERIC(16,8)` | YES | `0.000005` | Biaya gas transaksi (SOL). | `0.00000500` |
| `finality_status`| `VARCHAR(16)` | **NO** | `'confirmed'` | Status finalitas Solana (`confirmed`, `finalized`). | `'confirmed'` |
| `block_time` | `TIMESTAMPTZ` | **NO** | — | Waktu pencatatan blok blockchain. | `2026-10-14 14:28:10+07` |
| `raw_payload` | `JSONB` | YES | `'{}'::jsonb` | Payload data mentah JSON hasil respons RPC/Helius. | `{"slot": 28410291, ...}` |
| `ingested_at` | `TIMESTAMPTZ` | **NO** | `CURRENT_TIMESTAMP` | Waktu pipeline memasukkan data ke database. | `2026-10-14 14:28:15+07` |

---

## 3. Tabel: `tokens`
Menyimpan master data aset kripto yang diperdagangkan (SPL Token Solana dan pasangan Binance Spot).

| Kolom | Tipe Data | Nullable | Default | Deskripsi & Aturan Bisnis | Contoh Nilai |
|---|---|---|---|---|---|
| `id` | `UUID` | **NO** | `gen_random_uuid()` | Primary Key unik. | `c2eebc99-9c0b-4ef8-bb6d-6bb9bd380c33` |
| `address` | `VARCHAR(128)` | **NO** | — | Mint address Solana (Base58) atau Simbol Binance. **UNIQUE**. | `'SOLUSDT'` / `'DezX...PB263'` |
| `chain` | `VARCHAR(32)` | **NO** | `'solana'` | Jaringan / venue (`solana`, `binance_spot`, `bybit_spot` [roadmap]). | `'binance_spot'` |
| `symbol` | `VARCHAR(32)` | **NO** | — | Simbol ticker token. | `'SOL'` |
| `name` | `VARCHAR(128)` | YES | `NULL` | Nama lengkap aset. | `'Solana'` |
| `decimals` | `INT` | **NO** | `9` | Presisi desimal token. | `9` |
| `min_lot_size` | `NUMERIC(18,8)` | **NO** | `0.001` | Kuantitas order minimum exchange/DEX. | `0.01000000` |
| `tick_size` | `NUMERIC(18,8)` | **NO** | `0.01` | Presisi minimum fraksi harga order. | `0.01000000` |
| `is_blacklisted` | `BOOLEAN` | **NO** | `FALSE` | Flag blacklist dari Risk Engine. | `FALSE` |
| `freeze_authority_revoked` | `BOOLEAN` | **NO** | `TRUE` | Khusus Solana: Apakah freeze authority telah dicabut. | `TRUE` |
| `mint_authority_revoked` | `BOOLEAN` | **NO** | `TRUE` | Khusus Solana: Apakah mint authority telah dicabut. | `TRUE` |
| `pool_liquidity_usd` | `NUMERIC(18,2)` | YES | `0.00` | Kedalaman likuiditas kolam terkini. | `154000.00` |
| `created_at` | `TIMESTAMPTZ` | **NO** | `CURRENT_TIMESTAMP` | Waktu pencatatan master token. | `2026-10-14 14:00:00+07` |
| `updated_at` | `TIMESTAMPTZ` | **NO** | `CURRENT_TIMESTAMP` | Waktu audit keamanan token terakhir. | `2026-10-14 14:30:00+07` |

---

## 4. Tabel: `market_snapshots`
Data time-series harga pasar, spread bid-ask, dan likuiditas per menit.

| Kolom | Tipe Data | Nullable | Default | Deskripsi & Aturan Bisnis | Contoh Nilai |
|---|---|---|---|---|---|
| `id` | `UUID` | **NO** | `gen_random_uuid()` | Primary Key unik. | `d4eebc99-9c0b-4ef8-bb6d-6bb9bd380d44` |
| `token_id` | `UUID` | **NO** | — | Foreign Key ke `tokens(id)`. | `c2eebc99...` |
| `price_usd` | `NUMERIC(18,6)` | **NO** | — | Harga spot terkini setara USD. | `152.400000` |
| `price_native` | `NUMERIC(24,8)` | YES | `NULL` | Harga dalam satuan aset dasar (USDT / SOL). | `152.40000000` |
| `volume_24h_usd` | `NUMERIC(18,2)` | YES | `0.00` | Volume transaksi pasar 24 jam. | `450000000.00` |
| `pool_liquidity_usd` | `NUMERIC(18,2)` | YES | `0.00` | Total kedalaman likuiditas pool AMM / Orderbook. | `1250000.00` |
| `bid_price` | `NUMERIC(18,6)` | YES | `NULL` | Harga penawaran beli tertinggi (Best Bid). | `152.380000` |
| `ask_price` | `NUMERIC(18,6)` | YES | `NULL` | Harga penawaran jual terendah (Best Ask). | `152.420000` |
| `spread_pct` | `NUMERIC(6,4)` | YES | `0.0000` | Selisih persentase bid-ask. Hanya bermakna bila `bid_price` & `ask_price` terisi; bila salah satunya NULL (snapshot pool DEX), Risk Engine menganggap spread **tidak diketahui** dan gerbang spread gagal — nilai `0.0000` dari default kolom diabaikan. | `0.0262` |
| `source` | `VARCHAR(32)` | **NO** | `'Binance_WS'` | Sumber data yang ditulis kode: `Binance_WS` (default, `ingestion/binance.py`) dan `DEXSCREENER` (token SPL, ditulis saat swap BUY segar dari wallet copy-trade yang disetujui). `BYBIT_WS` roadmap. | `'Binance_WS'` |
| `snapshot_time` | `TIMESTAMPTZ` | **NO** | — | Timestamp data diterbitkan dari sumber. | `2026-10-14 14:31:00+07` |
| `is_stale` | `BOOLEAN` | **NO** | `FALSE` | True jika selisih waktu snapshot > 30 detik. | `FALSE` |

---

## 5. Tabel: `strategies` & `strategy_versions`
Mengelola katalog strategi trading dan parameter kuantitatif ter-versi.

### Tabel `strategies`
| Kolom | Tipe Data | Nullable | Default | Deskripsi | Contoh Nilai |
|---|---|---|---|---|---|
| `id` | `UUID` | **NO** | `gen_random_uuid()` | Primary Key. | `e5eebc99-9c0b...` |
| `name` | `VARCHAR(64)` | **NO** | — | Nama strategi (`MOMENTUM_BREAKOUT`). **UNIQUE**. | `'MOMENTUM_BREAKOUT'` |
| `description` | `TEXT` | YES | `NULL` | Penjelasan logika dasar strategi. | `'Breakout resistance terkonfirmasi volume 2x'` |
| `is_active` | `BOOLEAN` | **NO** | `TRUE` | Status aktifasi global strategi. | `TRUE` |
| `created_at` | `TIMESTAMPTZ` | **NO** | `CURRENT_TIMESTAMP` | Waktu dibuat. | `2026-10-14 14:00:00+07` |

### Tabel `strategy_versions`
| Kolom | Tipe Data | Nullable | Default | Deskripsi | Contoh Nilai |
|---|---|---|---|---|---|
| `id` | `UUID` | **NO** | `gen_random_uuid()` | Primary Key. | `f6eebc99-9c0b...` |
| `strategy_id` | `UUID` | **NO** | — | Foreign Key ke `strategies(id)`. | `e5eebc99...` |
| `version_tag` | `VARCHAR(16)` | **NO** | `'v1.0.0'` | Label versi semantik. | `'v1.0.0'` |
| `parameters_config` | `JSONB` | **NO** | `'{}'::jsonb` | Konfigurasi parameter numerik indikator dan SL/TP. | `{"ema_fast": 20, "ema_slow": 50, "risk_rr": 2.0}` |
| `is_default` | `BOOLEAN` | **NO** | `TRUE` | Versi aktif utama. | `TRUE` |
| `deployed_at` | `TIMESTAMPTZ` | **NO** | `CURRENT_TIMESTAMP` | Waktu versi diterapkan. | `2026-10-14 14:00:00+07` |

---

## 6. Tabel: `agent_runs` & `llm_requests`
Audit log eksekusi multi-agent Hermes dan konsumsi model AI eksternal.

### Tabel `agent_runs`
| Kolom | Tipe Data | Nullable | Default | Deskripsi | Contoh Nilai |
|---|---|---|---|---|---|
| `id` | `UUID` | **NO** | `gen_random_uuid()` | Primary Key unik eksekusi agen. | `11eebc99-9c0b...` |
| `strategy_version_id`| `UUID` | YES | `NULL` | Foreign Key ke `strategy_versions(id)`. | `f6eebc99...` |
| `agent_name` | `VARCHAR(32)` | **NO** | — | Nama agen (`TOKEN_SAFETY`, `MARKET_CONTEXT`, `STRATEGY_SIGNAL`). | `'STRATEGY_SIGNAL'` |
| `task_type` | `VARCHAR(32)` | **NO** | — | Jenis tugas (`REGIME_DETECTION`, `SIGNAL_SYNTHESIS`). | `'SIGNAL_SYNTHESIS'` |
| `status` | `VARCHAR(16)` | **NO** | `'STARTED'` | Status eksekusi (`STARTED`, `SUCCESS`, `FAILED`, `TIMEOUT`). | `'SUCCESS'` |
| `execution_time_ms` | `NUMERIC(8,2)` | YES | `0.00` | Total durasi eksekusi dalam milidetik. | `1450.25` |
| `created_at` | `TIMESTAMPTZ` | **NO** | `CURRENT_TIMESTAMP` | Waktu run dimulai. | `2026-10-14 14:32:00+07` |

### Tabel `llm_requests`
| Kolom | Tipe Data | Nullable | Default | Deskripsi | Contoh Nilai |
|---|---|---|---|---|---|
| `id` | `UUID` | **NO** | `gen_random_uuid()` | Primary Key panggilan inferensi LLM. | `22eebc99-9c0b...` |
| `agent_run_id` | `UUID` | **NO** | — | Foreign Key ke `agent_runs(id)`. | `11eebc99...` |
| `provider` | `VARCHAR(32)` | **NO** | `'OPENROUTER'` | Provider gateway (`OPENROUTER` / `9ROUTE`). | `'OPENROUTER'` |
| `model_name` | `VARCHAR(64)` | **NO** | — | Nama model LLM yang diakses. | `'anthropic/claude-haiku-5.5'` |
| `prompt_tokens` | `INT` | **NO** | `0` | Jumlah token prompt input. | `420` |
| `completion_tokens` | `INT` | **NO** | `0` | Jumlah token keluaran model. | `185` |
| `cost_usd` | `NUMERIC(8,6)` | YES | `0.000000` | Estimasi biaya pemanggilan kredit. | `0.000520` |
| `latency_ms` | `NUMERIC(8,2)` | **NO** | — | Durasi round-trip API LLM. | `850.50` |
| `status_code` | `INT` | **NO** | `200` | HTTP Status code respons. | `200` |
| `request_prompt_summary`| `JSONB` | YES | `'{}'::jsonb` | Ringkasan prompt tanpa data rahasia. | `{"task": "signal_score", "symbol": "SOLUSDT"}` |
| `response_json` | `JSONB` | YES | `'{}'::jsonb` | Respons terstruktur yang divalidasi Pydantic. | `{"action": "BUY", "confidence": 0.84}` |
| `requested_at` | `TIMESTAMPTZ` | **NO** | `CURRENT_TIMESTAMP` | Waktu permintaan dikirim. | `2026-10-14 14:32:01+07` |

---

## 7. Tabel: `trading_signals`
Menyimpan rekomendasi sinyal perdagangan yang dihasilkan agen AI sebelum dievaluasi risiko.

| Kolom | Tipe Data | Nullable | Default | Deskripsi & Aturan Bisnis | Contoh Nilai |
|---|---|---|---|---|---|
| `id` | `UUID` | **NO** | `gen_random_uuid()` | Primary Key sinyal. | `33eebc99-9c0b...` |
| `agent_run_id` | `UUID` | **NO** | — | Foreign Key ke `agent_runs(id)`. | `11eebc99...` |
| `token_id` | `UUID` | **NO** | — | Foreign Key ke `tokens(id)`. | `c2eebc99...` |
| `symbol` | `VARCHAR(32)` | **NO** | — | Simbol aset (`SOLUSDT`). | `'SOLUSDT'` |
| `action` | `VARCHAR(16)` | **NO** | — | Usulan tindakan: `BUY`, `SELL`, `HOLD`. | `'BUY'` |
| `target_entry_price` | `NUMERIC(18,6)` | **NO** | — | Rekomendasi harga masuk order. | `152.400000` |
| `suggested_stop_loss` | `NUMERIC(18,6)` | **NO** | — | Level Stop Loss wajib awal. | `149.350000` |
| `suggested_take_profit_1` | `NUMERIC(18,6)` | **NO** | — | Level TP1 (rasio 1.5R untuk 50% parsial). | `156.980000` |
| `suggested_take_profit_2` | `NUMERIC(18,6)` | **NO** | — | Level TP2 (rasio 3.0R untuk penutupan penuh). | `161.550000` |
| `recommended_allocation_pct` | `NUMERIC(5,4)` | **NO** | `0.0050` | Alokasi risiko modal (maksimal 0.005 = 0.5%). | `0.0050` |
| `confidence_score` | `NUMERIC(4,3)` | **NO** | — | Skor keyakinan model AI (0.000 s.d. 1.000). | `0.840` |
| `estimated_winrate_pct` | `NUMERIC(5,2)` | YES | `50.00` | Estimasi probabilitas win rate strategi. | `62.50` |
| `rationale` | `TEXT` | YES | `NULL` | Alasan ringkas analisis pasar. | `'Breakout resistance 152 terkonfirmasi volume'` |
| `status` | `VARCHAR(16)` | **NO** | `'PENDING'` | Status sinyal: `PENDING`, `REJECTED`, `EXECUTED`, `EXPIRED`. | `'EXECUTED'` |
| `generated_at` | `TIMESTAMPTZ` | **NO** | `CURRENT_TIMESTAMP` | Waktu sinyal diterbitkan. | `2026-10-14 14:32:02+07` |
| `expires_at` | `TIMESTAMPTZ` | **NO** | — | Batas waktu kedaluwarsa sinyal (default +5 menit). | `2026-10-14 14:37:02+07` |

---

## 8. Tabel: `risk_checks`
Mencatat hasil evaluasi 9 pintu keselamatan deterministik sebelum eksekusi diizinkan.

| Kolom | Tipe Data | Nullable | Default | Deskripsi & Aturan Bisnis | Contoh Nilai |
|---|---|---|---|---|---|
| `id` | `UUID` | **NO** | `gen_random_uuid()` | Primary Key evaluasi risiko. | `44eebc99-9c0b...` |
| `user_id` | `UUID` | **NO** | — | Foreign Key ke `users(id)` (migrasi 004). Satu sinyal dievaluasi per akun; maksimal satu verdict per (`user_id`, `trading_signal_id`), dijaga idempoten oleh `_process_signal`. | `a1eebc99...` |
| `trading_signal_id` | `UUID` | **NO** | — | Foreign Key ke `trading_signals(id)`. | `33eebc99...` |
| `passed` | `BOOLEAN` | **NO** | — | Status kelulusan mutlak: `TRUE` (Lolos) / `FALSE` (Tolak). | `TRUE` |
| `expectancy_check` | `BOOLEAN` | **NO** | — | Pintu 1: Ekspektasi matematis bersih biaya $> 0$. | `TRUE` |
| `risk_per_trade_check` | `BOOLEAN` | **NO** | — | Pintu 2: Nilai risiko per trade $\le 0.5\%$ ekuitas. | `TRUE` |
| `daily_loss_check` | `BOOLEAN` | **NO** | — | Pintu 3: Kerugian 24 jam terakhir $< 2.0\%$ ekuitas. | `TRUE` |
| `drawdown_check` | `BOOLEAN` | **NO** | — | Pintu 4: Drawdown dari High-Water Mark $< 8.0\%$. | `TRUE` |
| `spread_check` | `BOOLEAN` | **NO** | — | Pintu 5: Spread bid-ask $\le 0.08\%$ dan pool likuid. | `TRUE` |
| `stop_loss_check` | `BOOLEAN` | **NO** | — | Pintu 6: Stop Loss valid dan rasio R:R $\ge 1.5$. | `TRUE` |
| `balance_lot_check` | `BOOLEAN` | **NO** | — | Pintu 7: Saldo kas mencukupi dan memenuhi min lot. | `TRUE` |
| `circuit_breaker_check` | `BOOLEAN` | **NO** | — | Pintu 8a: Status sistem bukan dalam Circuit Breaker/Freeze. | `TRUE` |
| `max_positions_check` | `BOOLEAN` | **NO** | `TRUE` | Pintu 8b: Jumlah posisi terbuka < batas `MAX_OPEN_POSITIONS`. Ditambahkan via migrasi `003_risk_checks_max_positions`. | `TRUE` |
| `data_freshness_check` | `BOOLEAN` | **NO** | — | Pintu 9: Usia data harga pasar $< 30$ detik. | `TRUE` |
| `rejection_reasons` | `JSONB` | YES | `'[]'::jsonb` | Daftar array aturan yang gagal jika `passed == FALSE`. Kode dari Risk Gate Python (`gate.py`), plus kode IPC Rust engine bila `ENGINE_URL` diisi: `ENGINE_TIMEOUT`, `ENGINE_UNAVAILABLE`, `ENGINE_ERROR`, `ENGINE_INVALID_RESPONSE`, `ENGINE_REJECTED`, atau kode yang dikirim engine. Kolom gate boolean tetap mencerminkan evaluasi Python. | `[]` / `["DAILY_LOSS_LIMIT_EXCEEDED"]` / `["ENGINE_TIMEOUT"]` |
| `evaluated_at` | `TIMESTAMPTZ` | **NO** | `CURRENT_TIMESTAMP` | Waktu evaluasi aturan dieksekusi (latensi < 20ms). | `2026-10-14 14:32:02.015+07` |

---

## 9. Tabel: `paper_orders` & `paper_trades`
Mencatat order virtual dan transaksi pemenuhan eksekusi (*fills*) simulasi.

### Tabel `paper_orders`
| Kolom | Tipe Data | Nullable | Default | Deskripsi | Contoh Nilai |
|---|---|---|---|---|---|
| `id` | `UUID` | **NO** | `gen_random_uuid()` | Primary Key order virtual. | `55eebc99-9c0b...` |
| `risk_check_id` | `UUID` | **NO** | — | Foreign Key ke `risk_checks(id)`. **UNIQUE**. | `44eebc99...` |
| `client_order_id` | `VARCHAR(64)` | **NO** | — | Identifier idempotensi lokal. **UNIQUE**. | `'ORD-20261014-001'` |
| `symbol` | `VARCHAR(32)` | **NO** | — | Simbol aset (`SOLUSDT`). | `'SOLUSDT'` |
| `side` | `VARCHAR(8)` | **NO** | — | Sisi order: `BUY` atau `SELL`. | `'BUY'` |
| `order_type` | `VARCHAR(16)` | **NO** | `'MARKET'` | Tipe order: `MARKET` atau `LIMIT`. | `'MARKET'` |
| `requested_quantity` | `NUMERIC(24,8)`| **NO** | — | Kuantitas unit yang diminta berdasarkan rumus sizing 0.5%. | `16.79000000` |
| `requested_price` | `NUMERIC(18,6)`| **NO** | — | Harga acuan saat pengajuan order. | `152.400000` |
| `calculated_dollar_risk`| `NUMERIC(12,4)`| **NO** | — | Nilai dolar yang dipertaruhkan (0.5% ekuitas). | `51.2266` |
| `status` | `VARCHAR(16)` | **NO** | `'SUBMITTED'` | `SUBMITTED`, `PARTIAL_FILLED`, `FILLED`, `CANCELLED`. | `'FILLED'` |
| `created_at` | `TIMESTAMPTZ` | **NO** | `CURRENT_TIMESTAMP` | Waktu order disubmit. | `2026-10-14 14:32:02.050+07` |
| `updated_at` | `TIMESTAMPTZ` | **NO** | `CURRENT_TIMESTAMP` | Waktu status order terbarui. | `2026-10-14 14:32:02.120+07` |

### Tabel `paper_trades`
| Kolom | Tipe Data | Nullable | Default | Deskripsi | Contoh Nilai |
|---|---|---|---|---|---|
| `id` | `UUID` | **NO** | `gen_random_uuid()` | Primary Key eksekusi trade. | `66eebc99-9c0b...` |
| `paper_order_id` | `UUID` | **NO** | — | Foreign Key ke `paper_orders(id)`. Fill entry **dan** fill exit (TP1/TP2/SL) sama-sama dicatat pada order pembuka posisi, karena `paper_orders.risk_check_id` wajib (NOT NULL) sehingga exit tidak punya order sendiri. Sebelum audit 2026-10-26 kode exit menulis `position.id` di sini → FK gagal dan posisi tidak pernah tertutup (F-26). | `55eebc99...` |
| `position_id` | `UUID` | **NO** | — | Foreign Key ke `positions(id)`. | `77eebc99...` |
| `executed_quantity` | `NUMERIC(24,8)`| **NO** | — | Kuantitas token yang terisi pada fill ini. | `16.79000000` |
| `executed_price` | `NUMERIC(18,6)`| **NO** | — | Harga fill aktual setelah memperhitungkan slippage. | `152.480000` |
| `slippage_pct` | `NUMERIC(6,4)` | **NO** | `0.0000` | Persentase slippage simulasi ($+0.052\%$). | `0.0525` |
| `transaction_fee_usd` | `NUMERIC(12,4)`| **NO** | `0.0000` | Biaya bursa simulasi (Taker fee 0.10% untuk Binance / Bybit Spot = $2.56 USD). | `2.5601` |
| `gas_fee_native` | `NUMERIC(16,8)`| YES | `0.000005` | Biaya jaringan Solana simulasi. | `0.00000500` |
| `execution_venue` | `VARCHAR(32)` | **NO** | `'BINANCE_SPOT_SIM'`| Venue simulasi: `BINANCE_SPOT_SIM` (Primer Aktif), `BYBIT_SPOT_SIM` (Sekunder Roadmap), `SOLANA_DEX_SIM`. | `'BINANCE_SPOT_SIM'` |
| `executed_at` | `TIMESTAMPTZ` | **NO** | `CURRENT_TIMESTAMP` | Waktu trade terjadi. | `2026-10-14 14:32:02.150+07` |

---

## 10. Tabel: `positions`
Menyimpan posisi terbuka aktif dan mengelola parameter level keluar (*Partial TP1 50%*, *TP2*, *Trailing Stop*, *SL Breakeven*).

| Kolom | Tipe Data | Nullable | Default | Deskripsi & Aturan Bisnis | Contoh Nilai |
|---|---|---|---|---|---|
| `id` | `UUID` | **NO** | `gen_random_uuid()` | Primary Key posisi unik. | `77eebc99-9c0b...` |
| `user_id` | `UUID` | **NO** | — | Foreign Key ke `users(id)` (migrasi 004). Pemilik posisi. | `a1eebc99...` |
| `token_id` | `UUID` | **NO** | — | Foreign Key ke `tokens(id)`. | `c2eebc99...` |
| `symbol` | `VARCHAR(32)` | **NO** | — | Simbol aset (`SOLUSDT`). | `'SOLUSDT'` |
| `status` | `VARCHAR(16)` | **NO** | `'OPEN'` | Status: `OPEN`, `PARTIALLY_CLOSED`, `CLOSED`. | `'OPEN'` |
| `current_quantity` | `NUMERIC(24,8)`| **NO** | — | Kuantitas aset yang masih aktif dipegang. | `16.79000000` |
| `average_entry_price`| `NUMERIC(18,6)`| **NO** | — | Harga masuk rata-rata tertimbang FIFO. | `152.480000` |
| `current_stop_loss` | `NUMERIC(18,6)`| **NO** | — | Stop Loss aktif (digeser ke BE saat TP1 hit). | `149.350000` |
| `take_profit_1` | `NUMERIC(18,6)`| **NO** | — | Level TP1 (1.5R: Tutup 50% posisi). | `156.980000` |
| `take_profit_2` | `NUMERIC(18,6)`| **NO** | — | Level TP2 (3.0R: Tutup 100% sisa posisi). | `161.550000` |
| `is_tp1_hit` | `BOOLEAN` | **NO** | `FALSE` | Menandai apakah TP1 telah tereksekusi. | `FALSE` |
| `trailing_stop_price`| `NUMERIC(18,6)`| YES | `NULL` | Level trailing stop ATR jika diaktifkan. | `NULL` |
| `realized_pnl_usd` | `NUMERIC(16,4)`| **NO** | `0.0000` | Keuntungan/kerugian terealisasi bersih dari fee. | `0.0000` |
| `unrealized_pnl_usd` | `NUMERIC(16,4)`| YES | `0.0000` | Floating profit/loss terkini (mark-to-market). | `+35.2000` |
| `opened_at` | `TIMESTAMPTZ` | **NO** | `CURRENT_TIMESTAMP` | Waktu posisi pertama kali dibuka. | `2026-10-14 14:32:02+07` |
| `closed_at` | `TIMESTAMPTZ` | YES | `NULL` | Waktu seluruh posisi ditutup penuh. | `NULL` |
| `updated_at` | `TIMESTAMPTZ` | **NO** | `CURRENT_TIMESTAMP` | Waktu pembaruan harga mark-to-market terakhir. | `2026-10-14 14:35:00+07` |

---

## 11. Tabel: `portfolio_snapshots`
Mencatat riwayat ekuitas, High-Water Mark, dan metrik compounding portofolio (*Equity Ledger*).

| Kolom | Tipe Data | Nullable | Default | Deskripsi & Aturan Bisnis | Contoh Nilai |
|---|---|---|---|---|---|
| `id` | `UUID` | **NO** | `gen_random_uuid()` | Primary Key snapshot. | `88eebc99-9c0b...` |
| `user_id` | `UUID` | **NO** | — | Foreign Key ke `users(id)` (migrasi 004). Ledger per akun. | `a1eebc99...` |
| `total_equity_usd` | `NUMERIC(18,4)`| **NO** | — | Nilai total ekuitas portofolio (Kas + Posisi). | `10245.3200` |
| `cash_balance_usd` | `NUMERIC(18,4)`| **NO** | — | Saldo kas virtual yang belum digunakan. | `7685.1200` |
| `open_positions_value_usd`|`NUMERIC(18,4)`|**NO**| — | Total nilai pasar posisi terbuka saat ini. | `2560.2000` |
| `daily_realized_pnl_usd`| `NUMERIC(16,4)`| **NO** | `0.0000` | Realized PnL bersih hari kalender berjalan. | `+125.4000` |
| `daily_loss_pct` | `NUMERIC(5,2)` | **NO** | `0.00` | Persentase kerugian hari ini (Batas: 2.0%). | `0.45` |
| `high_water_mark_usd` | `NUMERIC(18,4)`| **NO** | — | Puncak tertinggi saldo ekuitas historis. | `10450.0000` |
| `current_drawdown_pct` | `NUMERIC(5,2)` | **NO** | `0.00` | Persentase drawdown terkini dari HWM (Batas: 8.0%). | `1.96` |
| `win_rate_pct` | `NUMERIC(5,2)` | YES | `0.00` | Persentase kemenangan trade agregat. | `58.20` |
| `profit_factor` | `NUMERIC(6,2)` | YES | `0.00` | Profit Factor kumulatif. | `1.43` |
| `net_expectancy_usd` | `NUMERIC(12,4)`| YES | `0.0000` | Rata-rata ekspektasi matematis per trade ($E > 0$). | `12.4500` |
| `snapshot_time` | `TIMESTAMPTZ` | **NO** | `CURRENT_TIMESTAMP` | Waktu snapshot dicatat. | `2026-10-14 14:35:00+07` |

---

## 12. Tabel: `user_settings` & `system_events`
Pengaturan parameter operasional dan audit log kejadian sistem.

### Tabel `user_settings`
| Kolom | Tipe Data | Nullable | Default | Deskripsi | Contoh Nilai |
|---|---|---|---|---|---|
| `key` | `VARCHAR(64)` | **NO** | — | Nama kunci konfigurasi unik (Primary Key). | `'MAX_RISK_PER_TRADE_PCT'` |
| `value` | `TEXT` | **NO** | — | Nilai konfigurasi. | `'0.005'` (0.5%) |
| `description` | `VARCHAR(255)`| YES | `NULL` | Penjelasan fungsi parameter. | `'Batas toleransi risiko per transaksi'` |
| `is_mutable` | `BOOLEAN` | **NO** | `TRUE` | Apakah dapat diubah melalui Dashboard Web. | `TRUE` |
| `updated_at` | `TIMESTAMPTZ` | **NO** | `CURRENT_TIMESTAMP` | Waktu perubahan konfigurasi. | `2026-10-14 14:00:00+07` |

### Tabel `system_events`
| Kolom | Tipe Data | Nullable | Default | Deskripsi | Contoh Nilai |
|---|---|---|---|---|---|
| `id` | `UUID` | **NO** | `gen_random_uuid()` | Primary Key kejadian sistem. | `99eebc99-9c0b...` |
| `event_type` | `VARCHAR(64)` | **NO** | — | Tipe: `CIRCUIT_BREAKER_TRIGGERED`, `EMERGENCY_STOP`, dll. | `'CIRCUIT_BREAKER_TRIGGERED'` |
| `severity` | `VARCHAR(16)` | **NO** | `'INFO'` | Tingkat keparahan: `INFO`, `WARNING`, `ERROR`, `CRITICAL`. | `'CRITICAL'` |
| `message` | `TEXT` | **NO** | — | Deskripsi lengkap kejadian operasional. | `'Daily Loss mencapai 2.05%. Seluruh entry dibekukan.'` |
| `metadata` | `JSONB` | YES | `'{}'::jsonb` | Konteks data kejadian tanpa rahasia. | `{"daily_loss_pct": 2.05, "equity": 9800.0}` |
| `created_at` | `TIMESTAMPTZ` | **NO** | `CURRENT_TIMESTAMP` | Waktu kejadian tercatat. | `2026-10-14 14:35:01+07` |

---

## 13. Tabel: `ingestion_errors` (Dead Letter Queue)
Mencatat pesan/event yang gagal diproses oleh pipeline ingestion data market (Dead Letter Queue). Dibuat oleh migrasi `002_ingestion_dlq_and_ohlcv`.

| Kolom | Tipe Data | Nullable | Default | Deskripsi & Aturan Bisnis | Contoh Nilai |
|---|---|---|---|---|---|
| `id` | `UUID` | **NO** | `gen_random_uuid()` | Primary Key unik entri DLQ. | `aa1ebc99-9c0b-4ef8-bb6d-6bb9bd380a11` |
| `source` | `VARCHAR(32)` | **NO** | — | Asal pipeline yang gagal (`BINANCE_WS`, `HELIUS_RPC`, `AGGREGATOR`). | `'BINANCE_WS'` |
| `reason` | `VARCHAR(32)` | **NO** | — | Kode penyebab kegagalan (`PARSE_ERROR`, `SCHEMA_MISMATCH`, `TIMEOUT`, `UNKNOWN`). | `'PARSE_ERROR'` |
| `reference` | `VARCHAR(128)` | YES | `NULL` | Identifier referensi opsional (misal: `tx_signature`, `symbol`). | `'SOLUSDT'` |
| `detail` | `JSONB` | **NO** | `'{}'::jsonb` | Payload mentah dan pesan error lengkap untuk debugging. | `{"raw": "...", "error": "missing field price"}` |
| `occurred_at` | `TIMESTAMPTZ` | **NO** | `now()` | Waktu kegagalan terjadi. Diindeks untuk query time-range. | `2026-10-14 14:31:00+07` |

**Indeks:** `ix_ingestion_errors_occurred_at` pada kolom `occurred_at`.

---

## 14. Tabel: `market_ohlcv`
Menyimpan data agregasi candlestick OHLCV (Open/High/Low/Close) per interval waktu untuk setiap token. Dibuat oleh migrasi `002_ingestion_dlq_and_ohlcv`, diisi oleh `aggregator.py`.

| Kolom | Tipe Data | Nullable | Default | Deskripsi & Aturan Bisnis | Contoh Nilai |
|---|---|---|---|---|---|
| `id` | `UUID` | **NO** | `gen_random_uuid()` | Primary Key unik candle. | `bb2ebc99-9c0b-4ef8-bb6d-6bb9bd380b22` |
| `token_id` | `UUID` | **NO** | — | Foreign Key ke `tokens(id)`. Wajib ada token terdaftar. | `c2eebc99...` |
| `interval` | `VARCHAR(8)` | **NO** | — | Timeframe candle yang ditulis `aggregator.py`: `M1`, `M5`, `H1`. Hermes membaca `M1`. | `'M1'` |
| `bucket_time` | `TIMESTAMPTZ` | **NO** | — | Waktu pembukaan candle (awal bucket interval). | `2026-10-14 14:31:00+07` |
| `open` | `NUMERIC(18,6)` | **NO** | — | Harga pembukaan candle setara USD. | `152.300000` |
| `high` | `NUMERIC(18,6)` | **NO** | — | Harga tertinggi selama interval. | `152.650000` |
| `low` | `NUMERIC(18,6)` | **NO** | — | Harga terendah selama interval. | `152.150000` |
| `close` | `NUMERIC(18,6)` | **NO** | — | Harga penutupan candle setara USD. | `152.480000` |
| `sample_count` | `INT` | **NO** | `0` | Jumlah tick/snapshot yang diagregasi ke dalam candle ini. | `47` |
| `created_at` | `TIMESTAMPTZ` | **NO** | `now()` | Waktu baris ditulis ke database. | `2026-10-14 14:32:00+07` |

**Indeks:** `ix_market_ohlcv_token_id` pada kolom `token_id`.  
**Unique Constraint:** `uq_market_ohlcv_token_interval_bucket` pada `(token_id, interval, bucket_time)` — mencegah duplikasi candle untuk pasangan token-interval-waktu yang sama.
