# GERBANG KESELAMATAN TRADING LANGSUNG (LIVE TRADING SAFETY GATE)
**Dokumen:** `docs/05-security/LIVE_TRADING_SAFETY_GATE.md`  
**Proyek:** AI Crypto Trading & Copy-Trading Platform (AUTO-TRADE-AA)  
**Versi:** 1.0.0 (Tahap 0)  
**Status:** Draf Resmi Keamanan  

---

Dokumen ini mendefinisikan batas arsitektur mutlak yang mengunci fitur perdagangan menggunakan dana riil (*Live Trading*) selama fase MVP, serta menetapkan kriteria prasyarat ketat yang wajib dipenuhi sebelum **Fase 7 (Live Trading)** dipertimbangkan.

---

## 1. Kebijakan Penguncian Live Trading pada MVP (Locked by Default)

1. **Penguncian Tingkat Arsitektur (Hardcoded Lock):**
   - Pada Fase 0 hingga Fase 6, kode sumber aplikasi **tidak memiliki fungsi penandatanganan transaksi blockchain (*signing transactions*)** menggunakan kunci privat.
   - Variabel konfigurasi `LIVE_TRADING_ENABLED` terkunci pada nilai `FALSE` secara mutlak dan tidak dapat diubah hanya dengan memodifikasi satu baris file `.env`.

   > [!IMPORTANT]
   > **[FIX 2.1] Mekanisme Enforcement 3-Layer (bukan hanya klaim dokumen):**
   > Klaim "hardcoded" wajib diimplementasikan dalam **tiga lapisan** agar tidak bypassable dengan patch lokal:
   >
   > **Layer 1 — Compile-time Absence (Structural Guard):**
   > Modul `execution/live_order_executor.py` (atau ekuivalennya) **tidak dibuat / tidak ada** di codebase pada Fase 0–6. Fungsi `sign_transaction()` dan `submit_transaction()` tidak boleh eksis dalam kode yang ter-deploy. Absensi file = absensi kemampuan.
   >
   > **Layer 2 — Runtime Guard (Code Flag):**
   > Setiap titik eksekusi order wajib memanggil guard function berikut sebelum melanjutkan:
   > ```python
   > def assert_paper_mode():
   >     if os.getenv("LIVE_TRADING_ENABLED", "FALSE").upper() != "FALSE":
   >         raise RuntimeError("[SAFETY GATE] Live trading flag detected — execution BLOCKED. Review required.")
   >     if LIVE_TRADING_ENABLED is not False:  # compile-time constant
   >         raise RuntimeError("[SAFETY GATE] Compile-time constant override detected — execution BLOCKED.")
   > ```
   > Konstanta `LIVE_TRADING_ENABLED = False` didefinisikan di `config/safety_constants.py` — **bukan** di `.env` — sehingga perubahan `.env` saja tidak cukup.
   >
   > **Layer 3 — Startup Assertion (Boot-time Check):**
   > Saat aplikasi pertama kali start, safety check otomatis dijalankan:
   > ```python
   > # Di entrypoint aplikasi (main.py / app_factory.py)
   > assert LIVE_TRADING_ENABLED is False, "[BOOT] Live trading must be disabled on startup."
   > assert not hasattr(execution_module, 'sign_transaction'), "[BOOT] sign_transaction must not exist."
   > logger.info("[SAFETY GATE] Paper mode verified. All 3 enforcement layers PASSED.")
   > ```
   > Aplikasi **tidak akan start** jika salah satu dari tiga layer ini gagal.

2. **Ketiadaan Akses Saldo Riil:**
   - Seluruh transaksi dieksekusi oleh mesin simulator `Paper Broker` dengan saldo virtual di database PostgreSQL. Kesalahan pengkodean (*bugs*) atau anomali pasar tidak akan pernah mengakibatkan kerugian finansial nyata.

---

## 2. Persyaratan Mutlak Sebelum Memasuki Fase 7 (Prerequisites)

Fitur Live Trading **TIDAK BOLEH** diaktifkan atau dikembangkan sebelum seluruh 6 kriteria keselamatan berikut berstatus lulus (**PASS**):

### Kriteria 1: Periode Observasi Paper Trading Minimum 30 Hari
- Sistem paper trading wajib telah berjalan secara kontinu minimal **30 hari kalender berturut-turut** di lingkungan pengujian.
- Menghasilkan **Positive Expectancy ($E > 0$)** dan Net PnL positif setelah memperhitungkan biaya bursa Binance Spot (0.1%) dan estimasi slippage realistis.

### Kriteria 2: Kepatuhan Drawdown & Stabilitas Tanpa Crash
- Selama 30 hari observasi, Maximum Drawdown portofolio simulasi **tidak pernah menyentuh atau melampaui batas 8.0%**.
- Tercatat **Zero Unhandled Exceptions / Crash** pada proses backend dan ingestion engine.

### Kriteria 3: Uji Petik Pemutusan Fisik Emergency Stop (Kill Switch Drill)
- Dilakukan simulasi pengujian tombol darurat `/kill` saat antrean pemrosesan sinyal sedang padat.
- Sistem terbukti memutus pembuatan order baru dalam waktu $\le 2.0$ detik sebanyak 5 kali pengujian berturut-turut tanpa kegagalan.

> [!NOTE]
> **[FIX 2.2] Definisi Metrik Pengukuran Kill Switch Drill:**
>
> | Parameter Pengukuran | Definisi |
> |---|---|
> | **T₀ (Start Point)** | Timestamp saat perintah `/kill` **diterima dan divalidasi** oleh Telegram Bot Handler (setelah chat ID allowlist check lolos). Bukan saat user menekan tombol. |
> | **T₁ (End Point)** | Timestamp saat flag `KILL_SWITCH_ACTIVE = True` **ter-persist ke database** AND semua consumer queue pemrosesan sinyal menerima sinyal shutdown (confirmed via queue.join() atau equivalent). |
> | **Latency yang Diukur** | `T₁ - T₀ ≤ 2.0 detik` |
> | **Tooling Pengujian** | Script `scripts/drill_kill_switch.py` yang men-inject sinyal ke queue secara programatik dan mengukur delta waktu dengan `time.perf_counter()`. Log direkam ke `logs/kill_switch_drill_{timestamp}.json`. |
> | **Definisi PASS** | Kelima run berturut-turut menghasilkan latency `≤ 2.0 detik` AND tidak ada order baru masuk ke `paper_orders` setelah T₁. |
> | **Definisi FAIL** | Salah satu run melebihi 2.0 detik, ATAU ditemukan order dengan `created_at > T₁` di tabel `paper_orders`. |
> | **Skenario In-Flight Request** | Untuk order yang **sudah dalam antrian** saat `/kill` diterima: order tersebut **boleh selesai diproses** (tidak dibatalkan paksa mid-execution untuk menghindari state korup), tetapi **tidak ada order baru** yang boleh masuk setelah T₁. Status order in-flight dicatat sebagai `COMPLETED_PRE_KILL`. |
> | **Kondisi Pengujian** | Queue harus berisi minimal 10 sinyal PENDING aktif saat drill dimulai untuk memvalidasi perilaku saat kondisi padat. |

### Kriteria 4: Isolasi Modal Menggunakan Burner Wallet
- Jika live trading diaktifkan di masa depan:
  - Dilarang keras menggunakan dompet utama (*Main Wallet*) atau dompet penyimpan aset dingin (*Cold Storage*).
  - Wajib menggunakan **Burner Wallet** khusus dengan alokasi modal kecil yang diisolasi (misal maksimal 1-2 SOL atau setara $150-$300 USD).
  - Kehilangan saldo pada burner wallet tidak boleh mengancam kelangsungan finansial pengguna.

> [!IMPORTANT]
> **[FIX 2.3] Enforcement Teknis Burner Wallet (bukan hanya kebijakan operasional):**
>
> Batas modal burner wallet wajib di-enforce secara teknis melalui **pre-order balance check** yang berjalan sebelum setiap order dikirim:
>
> ```python
> # Di execution/live_order_executor.py (aktif hanya saat Fase 7+)
> BURNER_WALLET_SOL_LIMIT = float(os.getenv("BURNER_WALLET_SOL_LIMIT", "2.0"))
>
> async def pre_order_balance_guard(wallet_address: str, rpc_client) -> None:
>     """Hard block: tolak order jika saldo wallet melebihi batas burner."""
>     balance_sol = await rpc_client.get_balance_sol(wallet_address)
>     if balance_sol > BURNER_WALLET_SOL_LIMIT:
>         raise SafetyGateError(
>             f"[BURNER WALLET GUARD] Saldo {balance_sol:.4f} SOL melebihi batas "
>             f"{BURNER_WALLET_SOL_LIMIT} SOL. Order DIBLOKIR. "
>             f"Pindahkan kelebihan saldo sebelum melanjutkan."
>         )
>     logger.info(f"[BURNER WALLET GUARD] Saldo {balance_sol:.4f} SOL ≤ {BURNER_WALLET_SOL_LIMIT} SOL — OK.")
> ```
>
> **Aturan enforcement tambahan:**
> | Aturan | Mekanisme |
> |---|---|
> | Saldo > batas saat startup | Aplikasi log warning kritis dan masuk mode read-only — tidak ada order baru. |
> | Saldo > batas mid-session | Setiap order baru diblokir oleh `pre_order_balance_guard()` sampai saldo turun di bawah batas. |
> | Batas dapat dikonfigurasi | Via env var `BURNER_WALLET_SOL_LIMIT` (default 2.0 SOL), **tidak bisa di-set ke nilai > 5.0 SOL** (hard cap di kode). |
> | Whitelist alamat | Hanya alamat yang terdaftar di `config/burner_wallets.json` yang dapat digunakan untuk live order. |
> | Alert otomatis | Jika saldo mendekati batas (> 80% dari limit), kirim alert Telegram ke operator. |

### Kriteria 5: Audit Kode Transaksi Mandiri (Independent Code Audit)
- Seluruh logika pembentukan transaksi Solana SPL dan penandatanganan instruksi DEX wajib diaudit secara baris per baris untuk memastikan ketiadaan *slippage uncapped* atau transfer tanpa batas.

### Kriteria 6: Persetujuan Eksplisit Pengguna (2-Step Human Confirmation)
- Live trading hanya dapat diaktifkan melalui checklist persetujuan tertulis formal dan konfirmasi dua langkah di antarmuka sistem.

---

## 3. Checklist Kesiapan Gerbang Keselamatan (Safety Gate Checklist)

| No | Parameter Kesiapan | Standar Target | Status Fase 0 |
|---|---|---|---|
| 1 | Masa Pengujian Paper Trading | $\ge 30$ Hari Kalender | **LOCKED (Belum Dimulai)** |
| 2 | Net Expectancy Portofolio | Positif ($E > 0$) Bersih Fee | **LOCKED** |
| 3 | Maximum Drawdown Historis | $< 8.0\%$ dari High-Water Mark | **LOCKED** |
| 4 | Stabilitas Backend Service | 0 Unhandled Crashes | **LOCKED** |
| 5 | Latensi Respons Emergency Stop | $\le 2.0$ Detik (Lolos Uji Drill) | **LOCKED** |
| 6 | Penggunaan Burner Wallet Terisolasi | Saldo Terkunci $\le 2$ SOL | **LOCKED** |
| 7 | Persetujuan Eksplisit Tertulis Operator | Ditandatangani Formal | **LOCKED** |

---

> [!CAUTION]
> Mengabaikan salah satu kriteria di atas atau mengaktifkan live trading secara prematur melanggar prinsip dasar keselamatan proyek dan membawa risiko kehilangan seluruh modal yang diperdagangkan.
