# KONTEKS SISTEM (SYSTEM CONTEXT)
**Dokumen:** `docs/02-architecture/SYSTEM_CONTEXT.md`  
**Proyek:** AI Crypto Trading & Copy-Trading Platform (AUTO-TRADE-AA)  
**Versi:** 1.0.0 (Tahap 0)  
**Status:** Draf Resmi Arsitektur  

---

## 1. Diagram Konteks Sistem (C4 Model - Level 1)

Diagram konteks sistem berikut menggambarkan hubungan batas sistem platform **AUTO-TRADE-AA** terhadap pengguna manusia dan entitas eksternal di sekitarnya.

```
                         ┌─────────────────────────────────┐
                         │   Operator Sistem (Human User)  │
                         │    (Solo Trader / Administrator)│
                         └───────────────┬─────────────────┘
                                         │
                         ┌───────────────┴─────────────────┐
                         │ Mengontrol, Meninjau, & Menguji │
                         │ HTTPS Web Browser / Telegram    │
                         ▼                                 ▼
         ┌───────────────────────────────┐ ┌───────────────────────────────┐
         │     Web Dashboard (Next.js)   │ │      Telegram Messenger       │
         └───────────────┬───────────────┘ └───────────────┬───────────────┘
                         │ HTTPS / REST                    │ HTTPS Webhook / Long-Poll
                         ▼                                 ▼
     ═════════════════════════════════════════════════════════════════════════════════
     ║               BATAS SISTEM: AUTO-TRADE-AA PLATFORM (LOCAL DOCKER)             ║
     ║                                                                               ║
     ║  ┌─────────────────────────────────────────────────────────────────────────┐  ║
     ║  │                     Backend Application Service (FastAPI)               │  ║
     ║  │   (Control API, Ingestion, Hermes Multi-Agent, Risk Gate, Paper Broker) │  ║
     ║  └────────────────────────────┬──────────────────┬─────────────────────────┘  ║
     ║                               │                  │                            ║
     ║                               ▼                  ▼                            ║
     ║                    ┌────────────────────┐ ┌──────────────┐                   ║
     ║                    │ PostgreSQL (DB)    │ │ Redis (Opt)  │                   ║
     ║                    └────────────────────┘ └──────────────┘                   ║
     ════════════════════════════════┼══════════════════┼═════════════════════════════
                                     │                  │
               HTTPS / RPC / WSS     │                  │ HTTPS JSON API
         ┌───────────────────────────┴────┐        ┌────┴────────────────────────────┐
         │                                │        │                                 │
         ▼                                ▼        ▼                                 ▼
┌──────────────────┐ ┌──────────────────┐ ┌──────────────────┐ ┌──────────────────┐
│ Binance Spot API │ │  Solana Network  │ │  OpenRouter API  │ │ Bybit Spot API   │
│ (Primary CEX-MVP)│ │  (RPC / Helius)  │ │ (LLM Provider 1) │ │ (Secondary-Roadm)│
└──────────────────┘ └──────────────────┘ └──────────────────┘ └──────────────────┘
```

---

## 2. Definisi Aktor & Sistem Eksternal

### 2.1 Aktor Internal & Pengguna
1. **Operator Sistem (Human Operator):**
   - Mengakses Dashboard Web melalui browser untuk memantau performa portofolio simulasi, melihat grafik PnL, dan mengonfigurasi watchlist wallet.
   - Mengirim perintah kontrol (`/status`, `/pause`, `/resume`, `/kill`) melalui Telegram untuk pengawasan jarak jauh.
2. **Platform AUTO-TRADE-AA (Core System):**
   - Beroperasi sebagai wadah aplikasi lokal pada MacBook M1 Pro yang mengelola pipeline ingestion, penalaran agen, gerbang risiko, dan simulasi order.

### 2.2 Sistem Eksternal & Protokol Integrasi

| Sistem Eksternal | Peran & Tanggung Jawab | Protokol Komunikasi | Format Data | Penanganan Kegagalan (Fallback) |
|---|---|---|---|---|
| **Binance Spot API (Bursa CEX Primer - Aktif MVP)** | Menyediakan stream harga real-time WebSocket (`@kline_1m`, `@trade`) dan REST API untuk instrumen likuiditas utama (`BTCUSDT`, `ETHUSDT`, `SOLUSDT`). | HTTPS REST (`api.binance.com`), WSS (`stream.binance.com:9443`) | JSON | Reconnecting WebSocket otomatis dengan exponential backoff; fallback ke snapshot REST jika WS terputus > 5s. |
| **Bybit Spot API (Bursa CEX Sekunder - Roadmap Rilis Mendatang)** | Bursa CEX sekunder yang dipertahankan untuk ekspansi multi-venue, cross-exchange arbitrage, dan redundansi likuiditas pada rilis mendatang. | HTTPS REST (`api.bybit.com`), WSS (`stream.bybit.com/v5/public/spot`) | JSON | Status standby/mock pada MVP; terisolasi tanpa memblokir pipeline eksekusi bursa primer. |
| **Solana RPC / Helius** | Menyediakan stream blok, signature transaksi akun, dan penguraian instruksi program DEX. | HTTPS (JSON-RPC 2.0), WSS (WebSocket) | JSON-RPC | Beralih ke node RPC publik cadangan; jika semua gagal, hentikan ingestion (*fail-closed*). |
| **Market Data Providers (DEXScreener / Birdeye / Raydium API)** | Menyediakan harga spot real-time, volume 24 jam, dan data kedalaman likuiditas pool DEX. | HTTPS REST API | JSON | Gunakan harga lokal dari transaksi swap on-chain terakhir jika usia data < 30 detik. |
| **OpenRouter API** | Penyedia inferensi AI primer (Claude, Llama, Gemini) untuk analisis token dan sentimen. | HTTPS REST | JSON (OpenAI-compatible) | Timeout 15 detik; otomatis dialihkan ke 9Route. |
| **9Route API** | Penyedia inferensi AI sekunder (*fallback provider*) jika OpenRouter mengalami kendala. | HTTPS REST | JSON (OpenAI-compatible) | Jika kedua provider gagal, tolak sinyal dan catat ke log audit. |
| **Telegram Bot API** | Kanal pengiriman notifikasi instan ke smartphone operator dan penerima perintah remote control. | HTTPS (Long Polling / Webhook) | Telegram JSON Bot API | Antrekan notifikasi di memori lokal; buang pesan non-kritis jika Telegram timeout. |

---

## 3. Asumsi Lingkungan & Batas Ketergantungan Eksternal
1. **Ketersediaan Jaringan Internet:** Sistem mengasumsikan koneksi internet host MacBook stabil untuk berkomunikasi dengan node Solana dan penyedia LLM.
2. **Batasan Kuota Layanan Gratis (Free Tier):**
   - Helius RPC: Dibatasi maksimal 100.000 kredit harian.
   - OpenRouter / 9Route: Dibatasi oleh saldo kredit prabayar atau kuota rate limit provider.
3. **Ketidaktersediaan Layanan Pihak Ketiga:** Tidak ada layanan eksternal yang dijamin memiliki SLA 100%. Sistem dirancang untuk dapat bertahan terhadap kegagalan sementara tanpa kehilangan integritas data internal.
