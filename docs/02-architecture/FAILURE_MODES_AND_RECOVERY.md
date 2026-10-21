# MODE KEGAGALAN DAN PEMULIHAN SISTEM (FAILURE MODES AND RECOVERY)
**Dokumen:** `docs/02-architecture/FAILURE_MODES_AND_RECOVERY.md`  
**Proyek:** AI Crypto Trading & Copy-Trading Platform (AUTO-TRADE-AA)  
**Versi:** 1.0.0 (Tahap 0)  
**Status:** Draf Resmi Arsitektur  

---

Dokumen ini mendokumentasikan skenario kegagalan potensial (*failure modes*), mekanisme deteksi, perilaku sistem (*fail-closed*), serta prosedur pemulihan otomatis dan manual untuk platform **AUTO-TRADE-AA**.

---

## 1. Matriks Penanganan Mode Kegagalan (Failure Matrix)

| ID Kegagalan | Komponen Terdampak | Gejala & Metode Deteksi | Dampak Sistem | Tindakan Otomatis (Fail-Closed) | Prosedur Pemulihan |
|---|---|---|---|---|---|
| **FM-01** | **Solana RPC Outage / Rate Limit** | HTTP 429/503 atau Timeout > 10s pada panggilan RPC. | Tidak ada data transaksi baru yang dapat ditarik. | Hentikan pembuatan sinyal copy-trade baru; tandai pipeline sebagai `DEGRADED`; terapkan exponential backoff. | Alihkan ke node RPC sekunder; jika pulih, lanjutkan sinkronisasi dari signature terakhir. |
| **FM-02** | **Stale Market Data (Data Harga Kadaluarsa)** | Timestamp snapshot pasar > 30 detik dari waktu sistem. | Harga token tidak mencerminkan kondisi riil pool DEX. | Risk Engine otomatis menolak pembuatan order baru (`REJECTED_STALE_DATA`). | Ingestion mencoba memperbarui snapshot harga; jika data segar masuk, sistem kembali normal. |
| **FM-03** | **Kegagalan AI Model Gateway (OpenRouter & 9Route)** | Kedua provider mengembalikan error 500, kuota habis, atau timeout > 15s. | Analisis token dan sinyal strategi AI tidak dapat diproses. | Sinyal dibatalkan (*dropped*); catat `LLMGatewayExhaustedError` ke log audit; kirim peringatan ke Telegram. | Sistem menunggu cooldown 60 detik; operator dapat mengganti API key atau beralih model via konfigurasi. |
| **FM-04** | **Format Keluaran AI Cacat (Schema Violation)** | Parser Pydantic gagal mengurai respons JSON dari LLM. | Data sinyal tidak valid secara struktural. | Lakukan 1 kali re-prompt perbaikan format; jika tetap gagal, buang sinyal tanpa memproses order. | Audit prompt untuk memeriksa ambiguitas instruksi. |
| **FM-05** | **Terputusnya Koneksi Basis Data PostgreSQL** | Exception `OperationalError: connection refused` dari SQLAlchemy. | Seluruh operasi pembacaan dan penulisan state gagal. | FastAPI mengembalikan HTTP 503; worker ingestion berhenti sementara (*pause loop*); jangan memproses order di memori. | Docker Compose me-restart kontainer PostgreSQL otomatis (`restart: unless-stopped`); pool koneksi menyambung ulang. |
| **FM-06** | **Gangguan Jaringan Telegram Bot API** | Panggilan webhook/polling Telegram timeout > 30s. | Notifikasi tidak terkirim dan perintah kontrol jarak jauh tertunda. | Antrekan notifikasi kritis di memori lokal (maksimal 100 pesan); operasi trading inti tetap berjalan. | Klien polling Telegram mencoba menyambung ulang secara berkala setiap 5 detik. |
| **FM-07** | **Tekanan Memori Host (OOM Risiko MacBook M1 Pro)** | Penggunaan RAM kontainer mendekati batas limit Docker. | Kontainer berisiko dimatikan paksa oleh Docker OOM Killer. | Driver Docker membatasi pertumbuhan alokasi memori sesuai batas tabel deployment. | Skrip worker melepaskan cache historis; lakukan pembersihan data sementara (*vacuum/prune*). |
| **FM-08** | **Pemicu Circuit Breaker Daily Loss Limit ($\ge 2.0\%$)** | Akumulasi kerugian terealisasi 24 jam mencapai atau melampaui 2.0% dari ekuitas awal hari. | Risiko kerugian beruntun intraday membahayakan portofolio. | Set `CIRCUIT_BREAKER_ACTIVE = true`; batalkan seluruh order `PENDING`; tolak entri baru; biarkan posisi terbuka dikawal SL/TP. | Jalankan investigasi pasar, evaluasi portofolio, dan eksekusi `/resume` setelah kondisi stabil (lihat SOP Lengkap). |
| **FM-09** | **Pemicu Circuit Breaker Drawdown Limit ($\ge 8.0\%$)** | Penurunan ekuitas mark-to-market mencapai atau melampaui 8.0% dari High-Water Mark. | Penurunan modal signifikan yang mengancam integritas strategi. | **System Freeze Total**: Set `CIRCUIT_BREAKER_ACTIVE = true` dan `TRADING_PAUSED = true`; kunci Risk Gate; kirim alert darurat. | Wajib melalui Checklist 10 Poin Pra-Resume dan Otorisasi Dua Langkah (`/confirm_reset_circuit` atau API parameter `force_drawdown_reset`). |
| **FM-10** | **Anomali Slippage Eksekusi ($> 0.50\%$) & Spread ($> 0.08\%$)** | Slippage eksekusi simulasi $> 0.50\%$ atau spread bid-ask $> 0.08\%$. | Biaya eksekusi mengikis expectancy positif sistem. | Pintu 5 Risk Gate otomatis menolak order (`SPREAD_OR_LIQUIDITY_INADEQUATE`); jika berulang 3x, pause strategi terkait. | Analisis kedalaman likuiditas pool DEX / orderbook Binance Spot; sesuaikan ambang batas atau blacklist instrumen. |

---

## 2. Prinsip Pemulihan dan Rekonsiliasi State (State Reconciliation)

Jika sistem mengalami crash atau restart mendadak di tengah pemrosesan:
1. **Startup Health Check & Self-Healing:**
   Saat kontainer backend menyala:
   - Memeriksa koneksi database dan menjalankan migrasi skema tertunda.
   - Mengambil signature transaksi terakhir yang berhasil disimpan dari tabel `wallet_observations` untuk melanjutkan sinkronisasi tanpa celah (*gap-less catchup*).
   - Memeriksa apakah ada `paper_orders` yang tertahan dalam status `SUBMITTED` saat restart terjadi; jika ditemukan, tandai order tersebut sebagai `EXPIRED` untuk menghindari eksekusi ganda yang terlambat.
2. **Rekonsiliasi Portofolio Virtual:**
   - Memvalidasi konsistensi pembukuan:  
     $$\text{Total Ekuitas Portofolio} = \text{Saldo Kas Virtual} + \sum (\text{Kuantitas Token Virtual} \times \text{Harga Pasar Terkini})$$
   - Jika ditemukan anomali pembukuan, status sistem otomatis dipindahkan ke `PAUSED` dan mengirimkan laporan inkonsistensi ke Telegram.

---

## 3. SOP Operasional Circuit Breaker & Pemulihan Sistem

Prosedur penanganan pemicu Circuit Breaker, verifikasi keselamatan pra-resume, alur state machine, dan runbook pemulihan manual operator didokumentasikan secara rinci pada dokumen terdedikasi:

👉 **[CIRCUIT_BREAKER_OPERATIONAL_SOP.md](file:///Users/nabilartanabil/SourceCode/AUTO-TRADE-AA/docs/05-security/CIRCUIT_BREAKER_OPERATIONAL_SOP.md)**

### Ringkasan Cepat Prosedur Pemulihan Operator:
1. **Periksa Status Sistem:** Kirim perintah `/status` via Telegram atau panggil `GET /control/status`.
2. **Inspeksi Log Backend:** Periksa penyebab pembekuan dengan `docker compose logs -f backend --tail=100`.
3. **Penuhi Checklist Pra-Resume:** Pastikan tidak ada posisi menggantung, data feed stabil ($\le 5$s), dan ekuitas terekonsiliasi.
4. **Buka Kunci Sistem (Unfreeze / Resume):**
   - **Kasus Normal / Daily Loss:** Kirim `/resume` via Telegram atau `POST /control/resume`.
   - **Kasus Drawdown $\ge 8.0\%$:** Wajib konfirmasi 2 langkah (`/resume` lalu ketik `/confirm_reset_circuit` dalam 60 detik).
   - **Kasus Darurat Ekstrem:** Pemicu `/kill` untuk pembatalan seketika dalam $\le 2.0$ detik.
