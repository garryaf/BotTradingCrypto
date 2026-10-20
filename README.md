# AUTO-TRADE-AA

> **AI-Powered Crypto Trading & Copy-Trading Platform**  
> *Hybrid Strategy (Binance Spot + Solana DEX) | Paper-Trading First | Deterministic Risk Gate (9 Pintu) | Fail-Closed Safety*

---

## 📖 Ringkasan Proyek

**AUTO-TRADE-AA** adalah platform perdagangan kripto cerdas berbasis agen AI (*Hermes Multi-Agent Orchestrator*) yang memadukan model inferensi probabilistik dengan mesin risiko deterministik (*Deterministic Risk Engine*). Sistem dirancang dengan prinsip **Safety-by-Design**, di mana AI hanya bertugas menganalisis dan merekomendasikan sinyal, sedangkan kode deterministik memegang kendali penuh atas validasi keselamatan dan eksekusi pesanan virtual (*Paper Trading*).

### Pilar Utama Sistem:
1. **Hybrid Market Engine:** Integrasi likuiditas institusional (Binance Spot API) dan peluang token terdesentralisasi on-chain (Solana Raydium/Orca DEX).
2. **Deterministic Risk Gate (9 Pintu):** Validasi serial ketat sebelum eksekusi (Risk 0.5% per trade, Daily Loss limit 2%, Drawdown limit 8%, Positive Expectancy, Freshness Check $\le$ 30 detik).
3. **Paper Trading First:** Simulasi akuntansi presisi dengan pemodelan slippage realistis, partial fill simulation, dan pemotongan biaya transaksi.
4. **Hardcoded Live Lock:** Eksekusi dana riil terkunci secara struktural dan runtime pada Fase 0 hingga Fase 6.
5. **Emergency Kill Switch:** Kemampuan pemutusan darurat total via Telegram Bot & Web Dashboard dalam waktu $\le 2.0$ detik.

---

## 🗺️ Roadmap Pengembangan

| Fase | Deskripsi | Status |
|---|---|---|
| **Fase 0** | **Dokumentasi Arsitektur, ERD, Flowchart, dan Spesifikasi Keamanan** | ✅ **SELESAI** |
| **Fase 1** | Infrastruktur Lokal Docker Compose, Database PostgreSQL Baseline, & API Scaffolding | ✅ **SELESAI** |
| **Fase 2** | Ingestion Engine (Binance Spot REST/WS, Solana RPC Polling, Deduplikasi, & DLQ) | 📅 *Terjadwal* |
| **Fase 3** | AI Model Gateway (OpenRouter + 9Route Fallback) & Hermes Multi-Agent Orchestrator | 📅 *Terjadwal* |
| **Fase 4** | Deterministic Risk Gate (9 Pintu) & Paper Broker Matching Engine Simulator | 📅 *Terjadwal* |
| **Fase 5** | Frontend Web Dashboard (Next.js 15) & Telegram Control Bot (/kill switch) | 📅 *Terjadwal* |
| **Fase 6** | Engine Backtesting Historis & Paper Trading Soak Test (30 Hari Stabilitas) | 📅 *Terjadwal* |
| **Fase 7** | Live Trading Safety Gate (Kondisional: Burner Wallet & Multi-Step Approval) | 🔒 *Terkunci* |

Detail rincian task setiap fase dapat dibaca pada [docs/00-overview/ROADMAP.md](file:///Users/nabilartanabil/SourceCode/AUTO-TRADE-AA/docs/00-overview/ROADMAP.md).

---

## 📂 Struktur Dokumentasi Proyek

Direktori [`docs/`](file:///Users/nabilartanabil/SourceCode/AUTO-TRADE-AA/docs) memuat spesifikasi lengkap:

- **[`docs/00-overview/`](file:///Users/nabilartanabil/SourceCode/AUTO-TRADE-AA/docs/00-overview):**
  - [PROJECT_CHARTER.md](file:///Users/nabilartanabil/SourceCode/AUTO-TRADE-AA/docs/00-overview/PROJECT_CHARTER.md) — Piagam proyek & batasan cakupan
  - [ROADMAP.md](file:///Users/nabilartanabil/SourceCode/AUTO-TRADE-AA/docs/00-overview/ROADMAP.md) — Rincian rencana kerja Fase 1–7
  - [OPEN_QUESTIONS.md](file:///Users/nabilartanabil/SourceCode/AUTO-TRADE-AA/docs/00-overview/OPEN_QUESTIONS.md) — Pertanyaan terbuka & keputusan baseline
  - [GLOSSARY.md](file:///Users/nabilartanabil/SourceCode/AUTO-TRADE-AA/docs/00-overview/GLOSSARY.md) — Istilah teknis & trading
- **[`docs/01-requirements/`](file:///Users/nabilartanabil/SourceCode/AUTO-TRADE-AA/docs/01-requirements):**
  - [BUSINESS_REQUIREMENTS.md](file:///Users/nabilartanabil/SourceCode/AUTO-TRADE-AA/docs/01-requirements/BUSINESS_REQUIREMENTS.md) — Kebutuhan bisnis
  - [FUNCTIONAL_REQUIREMENTS.md](file:///Users/nabilartanabil/SourceCode/AUTO-TRADE-AA/docs/01-requirements/FUNCTIONAL_REQUIREMENTS.md) — Kebutuhan fungsional sistem
  - [ACCEPTANCE_CRITERIA.md](file:///Users/nabilartanabil/SourceCode/AUTO-TRADE-AA/docs/01-requirements/ACCEPTANCE_CRITERIA.md) — Kriteria penerimaan modul
  - [TESTING_PLAN.md](file:///Users/nabilartanabil/SourceCode/AUTO-TRADE-AA/docs/01-requirements/TESTING_PLAN.md) — Rencana pengujian komprehensif
- **[`docs/02-architecture/`](file:///Users/nabilartanabil/SourceCode/AUTO-TRADE-AA/docs/02-architecture):**
  - [ARCHITECTURE_OVERVIEW.md](file:///Users/nabilartanabil/SourceCode/AUTO-TRADE-AA/docs/02-architecture/ARCHITECTURE_OVERVIEW.md) — Blueprint 8-box arsitektur sistem
  - [DATA_FLOW.md](file:///Users/nabilartanabil/SourceCode/AUTO-TRADE-AA/docs/02-architecture/DATA_FLOW.md) — Alur data end-to-end
  - [DEPLOYMENT_ARCHITECTURE.md](file:///Users/nabilartanabil/SourceCode/AUTO-TRADE-AA/docs/02-architecture/DEPLOYMENT_ARCHITECTURE.md) — Spesifikasi kontainer M1 Pro
- **[`docs/03-diagrams/`](file:///Users/nabilartanabil/SourceCode/AUTO-TRADE-AA/docs/03-diagrams):**
  - [DATA_FLOW.mmd](file:///Users/nabilartanabil/SourceCode/AUTO-TRADE-AA/docs/03-diagrams/DATA_FLOW.mmd) — Diagram alur data Mermaid
  - [ERD.mmd](file:///Users/nabilartanabil/SourceCode/AUTO-TRADE-AA/docs/03-diagrams/ERD.mmd) — Entity Relationship Diagram PostgreSQL
- **[`docs/04-data/`](file:///Users/nabilartanabil/SourceCode/AUTO-TRADE-AA/docs/04-data):**
  - [DATA_MODEL.md](file:///Users/nabilartanabil/SourceCode/AUTO-TRADE-AA/docs/04-data/DATA_MODEL.md) — Definisi skema tabel & tipe data
  - [DATABASE_MIGRATION_STRATEGY.md](file:///Users/nabilartanabil/SourceCode/AUTO-TRADE-AA/docs/04-data/DATABASE_MIGRATION_STRATEGY.md) — Panduan migrasi Alembic
- **[`docs/05-security/`](file:///Users/nabilartanabil/SourceCode/AUTO-TRADE-AA/docs/05-security):**
  - [LIVE_TRADING_SAFETY_GATE.md](file:///Users/nabilartanabil/SourceCode/AUTO-TRADE-AA/docs/05-security/LIVE_TRADING_SAFETY_GATE.md) — Protokol keselamatan live trading
  - [SECRET_MANAGEMENT.md](file:///Users/nabilartanabil/SourceCode/AUTO-TRADE-AA/docs/05-security/SECRET_MANAGEMENT.md) — Pengelolaan rahasia & sanitasi log

---

## 🚀 Panduan Memulai Cepat (Quickstart)

### Prasyarat Sistem:
- Mesin Host dengan Docker Desktop aktif (minimum RAM 8 GB dialokasikan ke Docker).
- Node.js v20+ LTS (untuk dashboard frontend).

### Backend (Fase 1 — PostgreSQL + FastAPI):
```bash
# 1. Salin template variabel lingkungan
cp .env.example .env
# Sesuaikan konfigurasi rahasia pada file .env (API Keys, Token DB, dsb.)
# CATATAN: Pastikan LIVE_TRADING_ENABLED tetap 'false'

# 2. Jalankan PostgreSQL & API backend (migrasi Alembic berjalan otomatis saat startup)
docker compose up -d postgres backend

# 3. Verifikasi
curl http://localhost:8000/api/v1/health
# -> {"status": "ok", "db": "connected"}
```

### Frontend (Dashboard Next.js):
```bash
cd frontend
npm install
npm run dev
# -> http://localhost:3000
```

---

## 🔒 Kebijakan Keamanan & Lisensi

Proyek ini menggunakan perlindungan keamanan berlapis. Kunci privat blockchain dilarang diimpor ke sistem pada fase MVP. Segala bentuk transaksi live trading hanya dapat diaktifkan setelah memenuhi 5 kriteria kelulusan formal.