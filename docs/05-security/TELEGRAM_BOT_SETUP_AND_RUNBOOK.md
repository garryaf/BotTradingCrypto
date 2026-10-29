# RUNBOOK SETUP & OPERASIONAL BOT TELEGRAM
**Dokumen:** `docs/05-security/TELEGRAM_BOT_SETUP_AND_RUNBOOK.md`  
**Proyek:** AI Crypto Trading & Copy-Trading Platform (AUTO-TRADE-AA)  
**Versi:** 1.0.0 (Fase 5)  
**Status:** Draf Resmi Operasional  
**Referensi:** [RBAC_AND_TELEGRAM_ACCESS.md](./RBAC_AND_TELEGRAM_ACCESS.md) · [`telegram_bot.py`](../../backend/src/control/telegram_bot.py)  

---

## 1. Prasyarat

- Akun Telegram aktif (aplikasi iOS / Android / Desktop).
- Akses ke file `.env` di root repositori.
- Container `backend` sudah berjalan (`docker compose up backend`).

---

## 2. Setup Bot Telegram (Satu Kali)

### Langkah 1 — Buat bot via BotFather

1. Buka Telegram, cari **@BotFather**.
2. Kirim perintah `/newbot`.
3. Masukkan **nama tampilan** bot (misal: `AutoTradeAA Control`).
4. Masukkan **username** bot (wajib diakhiri `bot`, misal: `autotrade_aa_bot`).
5. BotFather akan membalas dengan token berbentuk:
   ```
   123456789:AAFxxxxxxxxxxxxxxxxxxxxxxxxxx-xxxxxx
   ```
   Simpan token ini — **jangan bagikan ke siapapun**.

### Langkah 2 — Temukan Telegram User ID Anda

1. Buka Telegram, cari **@userinfobot**.
2. Kirim sembarang pesan.
3. Bot akan membalas dengan informasi termasuk `Id: 123456789`.
4. Catat angka tersebut — ini adalah `TELEGRAM_ALLOWED_USER_ID` Anda.

> **Mengapa User ID, bukan username?** Username dapat diubah kapan saja. User ID bersifat permanen dan tidak dapat dipalsukan.

### Langkah 3 — Konfigurasi `.env`

Buka `.env` di root repositori, isi dua variabel berikut:

```dotenv
TELEGRAM_BOT_TOKEN=123456789:AAFxxxxxxxxxxxxxxxxxxxxxxxxxx-xxxxxx
TELEGRAM_ALLOWED_USER_ID=123456789
# Wajib juga: chat tempat perintah diterima & alert dikirim. Untuk DM ke bot, Chat ID = User ID.
TELEGRAM_ALLOWED_CHAT_ID=123456789
```

> Tanpa `TELEGRAM_ALLOWED_CHAT_ID` bot mengabaikan **semua** perintah dan tidak bisa mengirim alert.

> **Keamanan:** Jangan commit file `.env` ke Git. File ini sudah terdaftar di `.gitignore`.

### Langkah 4 — Restart container backend

```bash
docker compose restart backend
```

Log sukses yang diharapkan:
```
INFO  control.telegram - Telegram bot polling started
```

Jika token tidak valid atau masih berisi nilai placeholder `1234567890`, bot akan idle dengan pesan:
```
WARNING  control.telegram - Telegram bot idle: TELEGRAM_BOT_TOKEN not configured
```

---

## 3. Panduan Perintah Bot

Semua perintah dikirim dari akun Telegram terdaftar ke bot secara langsung (DM ke bot).

### `/status` — Ringkasan Portofolio

**Gunakan saat:** Ingin memeriksa kondisi sistem dari jarak jauh.

**Contoh respons:**
```
🟢 RUNNING
Posisi terbuka (semua akun): 1
Circuit Breaker: off
```

| Field | Keterangan |
|---|---|
| Status atas | 🟢 RUNNING = aktif, 🔴 PAUSED = entry baru diblokir (pause global operator) |
| Posisi terbuka | Total posisi `OPEN`/`PARTIALLY_CLOSED` di semua akun |
| Circuit Breaker | `🚨 ACTIVE` jika circuit breaker global aktif |

> Bot adalah kanal **operator** (lintas akun). Equity, kas, PnL, dan drawdown per akun ada di dashboard (`/api/v1/portfolio`).

---

### `/positions` — Posisi Terbuka

**Gunakan saat:** Ingin melihat posisi terbuka beserta floating PnL dari jarak jauh.

**Contoh respons:**
```
📊 Posisi Terbuka:
BTCUSDT: 0.500000 @ $100.00 | PnL $12.34
```
Jika tidak ada posisi: `📭 Tidak ada posisi terbuka.`

---

### `/pause` — Jeda Entry Baru

**Gunakan saat:** Ingin menghentikan entry baru sementara tanpa menutup posisi yang sudah terbuka.

**Efek:**
- Menetapkan `user_settings.PAUSED = true` di database.
- Signal baru tidak akan dieksekusi.
- Posisi yang sudah terbuka tetap berjalan dan dipantau.

**Respons bot:**
```
⏸ Entry baru dihentikan sementara.
```

---

### `/resume` — Aktifkan Kembali Sistem

**Gunakan saat:** Ingin melanjutkan trading setelah pause manual atau Circuit Breaker.

> ⚠️ **Peringatan:** Perintah ini juga mereset Circuit Breaker secara bersamaan. Jalankan hanya setelah menyelesaikan 10-poin checklist pra-resume di [CIRCUIT_BREAKER_OPERATIONAL_SOP.md](./CIRCUIT_BREAKER_OPERATIONAL_SOP.md).

**Efek:**
- Menetapkan `PAUSED = false` dan `CIRCUIT_BREAKER_ACTIVE = false`.
- Entry baru diizinkan kembali pada siklus agent berikutnya.

**Respons bot:**
```
▶️ Sistem diaktifkan kembali (circuit breaker direset manual).
```

---

### `/kill` — Emergency Stop

**Gunakan saat:** Terjadi anomali pasar ekstrem, error kritis, atau situasi darurat lainnya.

**Efek (berurutan, < 2 detik):**
1. Set `PAUSED = true` dan `CIRCUIT_BREAKER_ACTIVE = true`.
2. Batalkan (`REJECTED`) semua `TradingSignal` berstatus `PENDING`.
3. Catat `SystemEvent` tipe `EMERGENCY_STOP` ke database.

**Respons bot:**
```
🛑 EMERGENCY STOP — 3 sinyal dibatalkan dalam 14.2ms.
```

> **Target latensi:** ≤ 2.000ms dari pengiriman perintah hingga sinyal dibatalkan (AC-CTL-01).

---

## 4. Mekanisme Keamanan — Silent Ignore

Perintah diproses hanya jika **chat** = `TELEGRAM_ALLOWED_CHAT_ID` **dan** (bila diisi) **pengirim** = `TELEGRAM_ALLOWED_USER_ID`. Selain itu:

- **Tidak mendapat respons apapun** (silent drop).
- Bot tidak mengonfirmasi keberadaannya kepada penyerang (*prevent reconnaissance*).
- Upaya akses tidak sah **tidak** dicatat ke `system_events` (belum diimplementasikan) — hanya diabaikan.

**Verifikasi dari kode** (`control/telegram_bot.py`, `_is_allowed`; diuji di `test_telegram_bot.py`):
```python
if not chat_id or chat_id != settings.telegram_allowed_chat_id:
    return False
if settings.telegram_allowed_user_id and from_id != settings.telegram_allowed_user_id:
    return False  # anggota lain di grup yang sama tidak bisa menjalankan /kill
```

---

## 5. Drill Verifikasi Penolakan Unauthorized (AC-CTL-02)

Prosedur untuk memverifikasi bahwa silent-drop berfungsi:

1. Temukan atau buat akun Telegram **kedua** (bisa akun teman/pengujian).
2. Dari akun kedua tersebut, kirim `/status` ke bot.
3. **Hasil yang diharapkan:** Tidak ada respons apapun dari bot.
4. Periksa database:
   ```sql
   SELECT * FROM system_events
   WHERE event_type = 'UNAUTHORIZED_ACCESS_ATTEMPT'
   ORDER BY created_at DESC LIMIT 5;
   ```
   > **Catatan:** Logging akses tidak sah ke `system_events` adalah perilaku yang didokumentasikan di RBAC; pastikan `telegram_bot.py` mengimplementasikannya jika belum ada.
5. Dokumentasikan hasil drill beserta timestamp sebagai bukti kepatuhan AC-CTL-02.

---

## 6. Troubleshooting

| Gejala | Kemungkinan Penyebab | Solusi |
|---|---|---|
| Bot tidak merespons sama sekali | Token belum dikonfigurasi atau salah | Cek log `WARNING control.telegram - Telegram bot idle` |
| Bot merespons "Error" | Container backend down atau DB tidak tersedia | `docker compose logs backend` |
| Perintah `/resume` tidak aktifkan system | Circuit Breaker perlu 2-step confirmation | Baca [CIRCUIT_BREAKER_OPERATIONAL_SOP.md](./CIRCUIT_BREAKER_OPERATIONAL_SOP.md) Seksi Reset |
| `/kill` terlalu lambat (> 2 detik) | Banyak PENDING signals atau DB lambat | Cek `system_events` untuk bottleneck; `elapsed_ms` ada di respons bot |
| Pesan masuk tapi bot tidak merespons | User ID tidak cocok dengan `TELEGRAM_ALLOWED_USER_ID` | Verifikasi ulang User ID via @userinfobot |

---

## 7. Item yang Dilewati / Risiko

- **Webhook mode** (vs long-polling): Bot menggunakan long-polling (`getUpdates`) karena tidak membutuhkan HTTPS endpoint publik di localhost. Upgrade ke webhook jika bot di-deploy ke server publik.
- **Logging unauthorized attempts**: RBAC doc menyebut pencatatan ke `system_events`, tapi `telegram_bot.py` saat ini hanya melakukan `continue` (silent drop) tanpa eksplisit menulis ke DB — implementasi logging ini menjadi risiko yang harus diselesaikan sebelum Fase 7.
