# AUTO-TRADE-AA

> **AI-Powered Crypto Trading & Copy-Trading Platform**  
> *Hybrid Strategy (Binance Spot + Solana DEX) | Paper-Trading First | Deterministic Risk Gate (9 Pintu) | Fail-Closed Safety*

---

## 📖 Ringkasan Proyek

**AUTO-TRADE-AA** adalah platform perdagangan aset kripto cerdas berbasis agen AI (*Hermes Multi-Agent Orchestrator*) yang memadukan model inferensi probabilistik dengan mesin risiko deterministik (*Deterministic Risk Engine*). Sistem dirancang dengan filosofi **Safety-by-Design**: AI hanya bertugas menganalisis data pasar dan menyintesis sinyal rekomendasi, sedangkan kode logika deterministik memegang kendali penuh atas evaluasi risiko, kalkulasi ukuran posisi, dan eksekusi pesanan virtual (*Paper Trading*).

### Pilar Keselamatan & Arsitektur Utama:
1. **Hybrid Market Engine:** Mengintegrasikan likuiditas institusional tersentralisasi (*Binance Spot REST & WebSocket*) dan peluang token on-chain desentralisasi (*Solana Raydium, Orca, Jupiter*).
2. **Deterministic Risk Gate (9 Pintu):** Evaluasi serial berurutan yang mutlak dipenuhi sebelum sinyal dieksekusi (Risk $\le 0.5\%$ per trade, Daily Loss limit $2\%$, Drawdown limit $8\%$, Positive Expectancy, Freshness Check $\le 30$ detik, Volatility/Spread check).
3. **Paper Trading Simulation Engine:** Simulasi akuntansi presisi dengan pemodelan slippage realistis, partial fill simulation, dan pemotongan biaya komisi transaksi.
4. **Hardcoded Live Lock:** Eksekusi dana riil (*live exchange execution*) terkunci secara struktural dan runtime pada konfigurasi default (`LIVE_TRADING_ENABLED=false`).
5. **Emergency Kill Switch:** Kemampuan pemutusan darurat total via Telegram Bot (`/kill`) & tombol darurat Dashboard Web dalam respon $\le 2.0$ detik.

---

## 🗺️ Roadmap Pengembangan

| Fase | Deskripsi | Status |
|---|---|---|
| **Fase 0** | **Dokumentasi Arsitektur, ERD, Flowchart, dan Spesifikasi Keamanan** | ✅ **SELESAI** |
| **Fase 1** | Infrastruktur Docker Compose, Database PostgreSQL Baseline, & API Scaffolding | ✅ **SELESAI** |
| **Fase 2** | Ingestion Engine (Binance Spot REST/WS, Solana RPC Polling, Deduplikasi, & DLQ) | ✅ **SELESAI** |
| **Fase 3** | AI Model Gateway (OpenRouter + 9Route Fallback) & Hermes Multi-Agent Orchestrator | ✅ **SELESAI** |
| **Fase 4** | Deterministic Risk Gate (9 Pintu) & Paper Broker Matching Engine Simulator | ✅ **SELESAI** |
| **Fase 5** | Frontend Web Dashboard (Next.js 15) & Telegram Control Bot (/kill switch) | ✅ **SELESAI** |
| **Fase 6** | Engine Backtesting Historis & Paper Trading Soak Test (30 Hari Stabilitas) | 🟡 *Tahap Uji Stabilitas* |
| **Fase 7** | Live Trading Safety Gate (Kondisional: Burner Wallet & Multi-Step Approval) | 🔒 *Terkunci Struktural* |

Detail rincian milestone: [docs/00-overview/ROADMAP.md](file:///Users/nabilartanabil/SourceCode/AUTO-TRADE-AA/docs/00-overview/ROADMAP.md)

---

## 🛠️ Tech Stack & Matriks Port

### Teknologi
- **Backend API & Orchestration:** Python 3.12, FastAPI, SQLModel (ORM), Alembic, AsyncPG, Pydantic v2.
- **Trading Engine:** Rust (komponen performa tinggi, IPC via HTTP lokal ke FastAPI).
- **AI Gateway:** OpenRouter (primer) + 9Route (fallback fail-over), Pydantic structured output.
- **Database:** PostgreSQL 16 (Alpine Linux).
- **Frontend Dashboard:** Next.js 15 (App Router), React 19, Tailwind CSS v4, Framer Motion, Lightweight Charts.
- **Control & Monitoring Bot:** Telegram Bot API (Async HTTPX Long-polling with allowlist security).
- **Infrastruktur & Orkestrasi:** Docker & Docker Compose, UFW Firewall, Nginx Reverse Proxy.

### Matriks Port & Endpoint

| Service | Port Internal / Host | Protokol | Deskripsi & Health URL |
|---|---|---|---|
| **FastAPI Backend** | `8000` | HTTP / WS | `http://localhost:8000/api/v1/health` |
| **PostgreSQL DB** | `5432` | TCP / SQL | `postgresql://autotrade_app:***@localhost:5432/autotrade_db` |
| **Frontend Web** | `3000` | HTTP | `http://localhost:3000` (Dashboard Utama) |
| **Rust Engine (IPC)** | `50051` / Internal | TCP | Engine mikro-latensi internal |

---

## 📂 Struktur Direktori Repository

```
AUTO-TRADE-AA/
├── backend/
│   ├── src/
│   │   ├── agents/          # Hermes Multi-Agent: hermes.py, skills.py, schemas.py
│   │   ├── api/             # FastAPI routes & control actions (/health, /signals, /portfolio)
│   │   ├── backtest/        # Backtesting engine, walk-forward analysis, data loader
│   │   ├── control/         # Telegram bot (long-polling, allowlist, /kill switch)
│   │   ├── gateway/         # AI Model Gateway (OpenRouter + 9Route fallback)
│   │   ├── ingestion/       # Binance Spot & Solana RPC ingestion pipelines
│   │   ├── risk/            # Risk Gate (9 pintu), broker simulator, balance ledger
│   │   ├── models.py        # SQLModel ORM (21 entitas tabel terelasi)
│   │   ├── config.py        # Pydantic Settings (manajemen konfigurasi terpusat)
│   │   └── main.py          # FastAPI application entry point
│   ├── alembic/             # Database migrations (alembic.ini + versions/)
│   └── Dockerfile           # Docker container backend
├── engine/                  # Rust Trading Engine (IPC via HTTP)
├── frontend/
│   ├── src/
│   │   ├── app/             # Next.js App Router (Dashboard, History, Settings)
│   │   ├── components/      # UI components (EquityHero, Mascots Bull/Bear, KillSwitch)
│   │   └── lib/             # API polling hooks & WebSocket subscribers
│   ├── Dockerfile           # Multi-stage production container Next.js
│   └── package.json
├── docs/                    # Dokumentasi lengkap sistem (15 domain lengkap)
├── .agents/                 # Aturan & skills AI agent (Ponytail rules)
├── .env.example             # Template konfigurasi variabel lingkungan
├── docker-compose.yml       # Docker Compose untuk local development
├── docker-compose.prod.yml  # Docker Compose untuk deployment production (VPS)
└── README.md
```

---

## 🚀 Panduan Deployment: Opsi 1 — Local Development Deployment

Gunakan opsi ini untuk pengujian lokal, eksperimen strategi paper-trading, dan pengembangan frontend/backend di laptop/PC pengembang.

### Prasyarat Sistem
- **OS:** macOS (Apple Silicon / Intel), Linux (Ubuntu/Debian), atau Windows 11 (WSL2).
- **Docker Desktop:** Versi 24.x ke atas (Alokasi RAM minimal 4 GB).
- **Node.js:** Versi 20 LTS (wajib jika menjalankan frontend di luar Docker).
- **Git:** Versi 2.x+.

---

### Step 1: Clone Repository
Buka terminal dan unduh kode sumber:
```bash
git clone https://github.com/Angga47/AUTO-TRADE-AA.git
cd AUTO-TRADE-AA
```

---

### Step 2: Konfigurasi File Lingkungan (`.env`)
Salin file template `.env.example` menjadi `.env`:
```bash
cp .env.example .env
```

Buka file `.env` dan atur parameter kunci:
```dotenv
# --- DATABASE CONFIGURATION ---
POSTGRES_DB=autotrade_db
POSTGRES_USER=autotrade_app
POSTGRES_PASSWORD=rahasia_password_lokal_123
DATABASE_URL=postgresql+asyncpg://autotrade_app:rahasia_password_lokal_123@localhost:5432/autotrade_db

# --- BACKEND SECRET ---
BACKEND_API_SECRET=super_secret_local_key_min_32_characters_long

# --- SAFETY LOCK (WAJIB FALSE DI DEVELOPMENT) ---
APP_ENV=development
LIVE_TRADING_ENABLED=false
INITIAL_PAPER_CAPITAL_USD=10000.00

# --- AI GATEWAY (Opsional untuk testing, butuh jika generate sinyal AI live) ---
OPENROUTER_API_KEY=sk-or-v1-xxxxxxxxxxxxxxxxxxxxxxx

# --- TELEGRAM BOT (Opsional di lokal) ---
TELEGRAM_BOT_TOKEN=
TELEGRAM_ALLOWED_USER_ID=
TELEGRAM_ALLOWED_CHAT_ID=
```

---

### Step 3: Jalankan Database & Backend via Docker Compose
Jalankan container PostgreSQL dan FastAPI Backend:
```bash
docker compose up -d --build postgres backend
```

Sistem akan otomatis:
1. Menyalakan PostgreSQL dan menunggu inisialisasi sampai status *healthy*.
2. Menjalankan migrasi database via Alembic (`alembic upgrade head`) untuk membuat 21 tabel.
3. Menjalankan server FastAPI pada port `8000`.

**Verifikasi status backend:**
```bash
curl http://localhost:8000/api/v1/health
# Output yang diharapkan:
# {"status":"ok","db":"connected","env":"development","live_trading":false}
```

**Melihat log realtime:**
```bash
docker compose logs -f backend
```

---

### Step 4: Jalankan Frontend Dashboard (Next.js)
Buka tab terminal baru dan jalankan frontend:
```bash
cd frontend
npm install
npm run dev
```

Buka peramban (browser) di: **`http://localhost:3000`**

---

### Step 5: Eksekusi Test Suite & Backtest
Pastikan semua komponen lulus validasi unit & integrasi:

```bash
# 1. Jalankan unit test dengan coverage minimal 85%
docker compose exec backend pytest tests/ --cov=src --cov-report=term-missing

# 2. Jalankan engine backtesting simulasi data historis BTCUSDT
docker compose exec backend python -m src.backtest.engine
```

---

### Step 6: Mematikan Service Lokal
```bash
# Mematikan service (data database tetap tersimpan di .data/postgres_data)
docker compose down

# Mematikan dan MENGHAPUS seluruh database lokal (Reset bersih)
docker compose down -v
rm -rf .data/
```

---

## 🌐 Panduan Deployment: Opsi 2 — Production VPS Deployment (Ubuntu Linux)

Panduan ini ditujukan untuk deployment pada VPS (Virtual Private Server) seperti AWS EC2, DigitalOcean, Hetzner, Vultr, atau Linode dengan pengamanan bertingkat (*Production-Ready Hardening*).

### Rekomendasi Spesifikasi Server
- **OS:** Ubuntu 22.04 LTS / 24.04 LTS x86_64
- **CPU:** 2 vCPU atau lebih
- **RAM:** Minimal 4 GB (disarankan 8 GB untuk build multi-container)
- **Disk:** Minimal 40 GB NVMe/SSD
- **Domain:** Telah diarahkan A-Record ke IP publik VPS (contoh: `trade.domainanda.com`)

---

### Step 1: Persiapan Server & Keamanan Jaringan (UFW Firewall)

Login ke VPS Anda via SSH:
```bash
ssh root@<IP_SERVER_ANDA>
```

Update repositori paket OS dan buat user non-root:
```bash
apt-get update && apt-get upgrade -y
apt-get install -y git curl ufw certbot python3-certbot-nginx nginx

# Buat pengguna operasional 'trader'
adduser trader
usermod -aG sudo trader
su - trader
```

Konfigurasi Firewall (UFW) — **Sangat Penting:**
Pastikan hanya port SSH, HTTP, dan HTTPS yang terbuka ke publik. **Port 5432 (Postgres) dan 8000 (Backend API internal) HARUS DITUTUP dari akses internet langsung**:
```bash
sudo ufw default deny incoming
sudo ufw default allow outgoing
sudo ufw allow 22/tcp    # SSH
sudo ufw allow 80/tcp    # HTTP (Nginx / Certbot)
sudo ufw allow 443/tcp   # HTTPS (Nginx)
sudo ufw enable
```

---

### Step 2: Instalasi Docker Engine & Docker Compose Plugin
Jalankan script resmi instalasi Docker di Ubuntu:
```bash
curl -fsSL https://get.docker.com -o get-docker.sh
sudo sh get-docker.sh
sudo usermod -aG docker $USER
# Terapkan perubahan grup:
newgrp docker
```

Verifikasi instalasi:
```bash
docker --version
docker compose version
```

---

### Step 3: Clone Repository & Persiapan Direktori Kerja
```bash
cd ~
git clone https://github.com/Angga47/AUTO-TRADE-AA.git
cd AUTO-TRADE-AA
```

---

### Step 4: Konfigurasi File Lingkungan Produksi (`.env`)
Buat file konfigurasi `.env` dengan kredensial kuat:
```bash
cp .env.example .env
chmod 600 .env
nano .env
```

Contoh konfigurasi standar produksi:
```dotenv
# ==============================================================================
# ENVIRONMENT UTAMA
# ==============================================================================
APP_ENV=production
DEBUG=false

# ==============================================================================
# DATABASE (PostgreSQL)
# ==============================================================================
POSTGRES_DB=autotrade_prod_db
POSTGRES_USER=autotrade_admin
# Gunakan generator string acak (min 32 karakter)
POSTGRES_PASSWORD=GantiDenganPasswordAcakSangatKuatDanPanjang987!
DATABASE_URL=postgresql+asyncpg://autotrade_admin:GantiDenganPasswordAcakSangatKuatDanPanjang987!@postgres:5432/autotrade_prod_db

# ==============================================================================
# SECURITY & AUTHENTICATION
# ==============================================================================
# Generate acak: openssl rand -hex 32
BACKEND_API_SECRET=f3a1b9c8d7e6f5a4b3c2d1e0f9a8b7c6d5e4f3a2b1c0d9e8f7a6b5c4d3e2f1a0
# WAJIB — backend menolak start tanpa dua kunci ini. User pertama yang mendaftar di /register menjadi admin.
# JWT_SECRET_KEY: openssl rand -hex 32
JWT_SECRET_KEY=GantiDenganHexAcak64Karakter
# FIELD_ENCRYPTION_KEY: python -c "from cryptography.fernet import Fernet; print(Fernet.generate_key().decode())"
FIELD_ENCRYPTION_KEY=GantiDenganKunciFernet

# ==============================================================================
# SAFETY LOCK RULES (PENTING)
# ==============================================================================
# Tetap FALSE! Eksekusi live dilarang sebelum uji stabilitas 30 hari selesai
LIVE_TRADING_ENABLED=false
INITIAL_PAPER_CAPITAL_USD=10000.00
MAX_RISK_PER_TRADE_PCT=0.005      # 0.5%
DAILY_LOSS_LIMIT_PCT=0.02         # 2%
MAX_DRAWDOWN_LIMIT_PCT=0.08       # 8%

# ==============================================================================
# AI MODEL GATEWAY (OPENROUTER)
# ==============================================================================
OPENROUTER_API_KEY=sk-or-v1-xxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx
OPENROUTER_DEFAULT_MODEL=anthropic/claude-3.5-sonnet

# ==============================================================================
# TELEGRAM CONTROL BOT (EMERGENCY RUNBOOK)
# ==============================================================================
TELEGRAM_BOT_TOKEN=123456789:ABCdefGhIJKlmNoPQRsTUVwxyZ_12345678
TELEGRAM_ALLOWED_USER_ID=987654321
TELEGRAM_ALLOWED_CHAT_ID=987654321

# ==============================================================================
# FRONTEND API BINDING
# ==============================================================================
NEXT_PUBLIC_API_URL=https://trade.domainanda.com/api
```

---

### Step 5: Jalankan Stack Produksi via `docker-compose.prod.yml`
Gunakan template produksi yang membungkus PostgreSQL, Backend, dan Frontend ke jaringan terisolasi (`127.0.0.1` binding):

```bash
docker compose -f docker-compose.prod.yml up -d --build
```

Cek status seluruh container:
```bash
docker compose -f docker-compose.prod.yml ps
```
Semua container (`postgres`, `backend`, `frontend`) harus berstatus `Up (healthy)` atau `Up`.

---

### Step 6: Konfigurasi Nginx Reverse Proxy & SSL (HTTPS)

Buat file konfigurasi virtual host Nginx:
```bash
sudo nano /etc/nginx/sites-available/autotrade.conf
```

Salin template konfigurasi berikut (sesuaikan nama domain):
```nginx
# Konfigurasi Nginx untuk AUTO-TRADE-AA
server {
    listen 80;
    server_name trade.domainanda.com;

    # Gzip Compression
    gzip on;
    gzip_types text/plain text/css application/json application/javascript text/xml application/xml application/xml+rss text/javascript;

    # 1. Routing API Backend & WebSocket
    location /api/ {
        proxy_pass http://127.0.0.1:8000/api/;
        proxy_http_version 1.1;
        proxy_set_header Upgrade $http_upgrade;
        proxy_set_header Connection "upgrade";
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
        proxy_read_timeout 86400;
    }

    # 2. Routing Frontend Dashboard
    location / {
        proxy_pass http://127.0.0.1:3000;
        proxy_http_version 1.1;
        proxy_set_header Upgrade $http_upgrade;
        proxy_set_header Connection "upgrade";
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
    }
}
```

Aktifkan konfigurasi dan reload Nginx:
```bash
sudo ln -s /etc/nginx/sites-available/autotrade.conf /etc/nginx/sites-enabled/
sudo nginx -t
sudo systemctl reload nginx
```

Pasang sertifikat SSL gratis via Let's Encrypt / Certbot:
```bash
sudo certbot --nginx -d trade.domainanda.com
```
Pilih opsi pengalihan otomatis ke HTTPS (*Redirect all HTTP traffic to HTTPS*).

---

### Step 7: Otomasi Backup Harian Database PostgreSQL
Pastikan data riwayat trade dan ledger aman dengan cron job backup otomatis.

Buat script backup di `/home/trader/backup_db.sh`:
```bash
cat << 'EOF' > /home/trader/backup_db.sh
#!/bin/bash
BACKUP_DIR="/home/trader/db_backups"
TIMESTAMP=$(date +"%Y%m%d_%H%M%S")
mkdir -p "$BACKUP_DIR"

# Dump database dari container postgres
docker compose -f /home/trader/AUTO-TRADE-AA/docker-compose.prod.yml exec -T postgres \
  pg_dump -U autotrade_admin autotrade_prod_db | gzip > "$BACKUP_DIR/autotrade_backup_$TIMESTAMP.sql.gz"

# Hapus backup yang lebih tua dari 14 hari
find "$BACKUP_DIR" -type f -name "*.sql.gz" -mtime +14 -delete
EOF

chmod +x /home/trader/backup_db.sh
```

Pasang di Cron Job (dieksekusi setiap pukul 02:00 pagi):
```bash
crontab -e
# Tambahkan baris berikut:
0 2 * * * /home/trader/backup_db.sh > /dev/null 2>&1
```

---

### Step 8: Verifikasi Deployment Akhir (Smoke Test Checklist)

Jalankan checklist verifikasi berikut dari luar server:

| Uji | Perintah / Prosedur | Hasil yang Diharapkan |
|---|---|---|
| **HTTPS SSL Valid** | Buka `https://trade.domainanda.com` di browser | Tanda gembok aman, sertifikat Let's Encrypt aktif |
| **API Healthcheck** | `curl -s https://trade.domainanda.com/api/v1/health` | `{"status":"ok","db":"connected"}` |
| **Circuit Breaker** | Kirim perintah `/status` ke Telegram Bot | Bot membalas ringkasan PnL, equity, dan kill switch state |
| **Database Migrations** | `docker compose -f docker-compose.prod.yml exec postgres psql -U autotrade_admin -d autotrade_prod_db -c "\dt"` | Menampilkan minimal 21 tabel |
| **Fail-Closed Safety** | Cek log backend: `docker compose logs backend \| grep LIVE_TRADING` | `LIVE_TRADING_ENABLED: False (Hard-locked)` |

---

## 🛑 Prosedur Darurat & Telegram Bot Control

Platform dilengkapi integrasi bot kontrol berkecepatan tinggi ($\le 2.0$ detik) untuk kondisi darurat:

### Perintah Utama Telegram Bot:
- `/status` — Menampilkan saldo portofolio, status pasar, drawdowns saat ini, dan mode trading.
- `/positions` — Menampilkan posisi terbuka beserta kalkulasi floating PnL realtime.
- `/kill` — **EMERGENCY STOP (SOP-01):** Membatalkan seluruh order tertunda, melikuidasi posisi aktif (jika mode pasar kritis), dan membekukan seluruh pembuatan order baru seketika.
- `/resume` — Memulihkan operasional sistem setelah investigasi insiden selesai dan persetujuan diberikan.

Panduan operasional lengkap: [`docs/05-security/TELEGRAM_BOT_SETUP_AND_RUNBOOK.md`](file:///Users/nabilartanabil/SourceCode/AUTO-TRADE-AA/docs/05-security/TELEGRAM_BOT_SETUP_AND_RUNBOOK.md)  
SOP Circuit Breaker: [`docs/05-security/CIRCUIT_BREAKER_OPERATIONAL_SOP.md`](file:///Users/nabilartanabil/SourceCode/AUTO-TRADE-AA/docs/05-security/CIRCUIT_BREAKER_OPERATIONAL_SOP.md)

---

## 🚨 Troubleshooting Operasional

| Masalah | Analisis Penyebab | Langkah Solusi |
|---|---|---|
| `backend` restart berulang kali (*CrashLoop*) | Database belum siap menerima koneksi saat migrasi | Cek log database: `docker compose logs postgres`. Pastikan string `DATABASE_URL` di `.env` memakai prefix `postgresql+asyncpg://`. |
| Port `5432` atau `8000` sudah digunakan | Ada service PostgreSQL atau Python lokal yang sedang jalan di host | Matikan service host: `sudo systemctl stop postgresql` atau ubah port host pada `docker-compose.yml`. |
| Telegram Bot tidak membalas pesan | `TELEGRAM_ALLOWED_USER_ID` salah atau bot token tidak valid | Dapatkan User ID numerik Anda via `@userinfobot`, update di `.env`, lalu restart backend: `docker compose restart backend`. |
| Nginx 502 Bad Gateway | Container backend/frontend down atau port internal tidak cocok | Periksa apakah container aktif via `docker compose ps`, dan pastikan proxy pass mengarah ke `127.0.0.1:8000` dan `127.0.0.1:3000`. |
| Error CORS saat panggil API dari frontend | Domain frontend belum diizinkan di backend CORS | Pastikan `NEXT_PUBLIC_API_URL` sesuai dengan URL domain yang digunakan. |

---

## 📚 Indeks Dokumentasi Lengkap (15 Domain)

Sistem didukung oleh dokumentasi teknis komprehensif yang telah diaudit memenuhi standar kualitas 100%:

| No | Domain Dokumentasi | Dokumen Utama |
|---|---|---|
| **01** | Gambaran & Roadmap | [docs/00-overview/ROADMAP.md](file:///Users/nabilartanabil/SourceCode/AUTO-TRADE-AA/docs/00-overview/ROADMAP.md) |
| **02** | Kebutuhan Fungsional (BR/FR) | [docs/01-requirements/FUNCTIONAL_REQUIREMENTS.md](file:///Users/nabilartanabil/SourceCode/AUTO-TRADE-AA/docs/01-requirements/FUNCTIONAL_REQUIREMENTS.md) |
| **03** | Kriteria Penerimaan (AC) | [docs/01-requirements/ACCEPTANCE_CRITERIA.md](file:///Users/nabilartanabil/SourceCode/AUTO-TRADE-AA/docs/01-requirements/ACCEPTANCE_CRITERIA.md) |
| **04** | Metodologi & Rencana Pengujian | [docs/01-requirements/TESTING_PLAN.md](file:///Users/nabilartanabil/SourceCode/AUTO-TRADE-AA/docs/01-requirements/TESTING_PLAN.md) |
| **05** | Spesifikasi UI/UX (Maskot & Dashboard) | [docs/01-requirements/UI_UX_SPECIFICATION.md](file:///Users/nabilartanabil/SourceCode/AUTO-TRADE-AA/docs/01-requirements/UI_UX_SPECIFICATION.md) |
| **06** | Arsitektur Sistem & ADR | [docs/02-architecture/ARCHITECTURE_OVERVIEW.md](file:///Users/nabilartanabil/SourceCode/AUTO-TRADE-AA/docs/02-architecture/ARCHITECTURE_OVERVIEW.md) |
| **07** | Spesifikasi Rust Trading Engine | [docs/02-architecture/RUST_ENGINE_INTEGRATION_SPEC.md](file:///Users/nabilartanabil/SourceCode/AUTO-TRADE-AA/docs/02-architecture/RUST_ENGINE_INTEGRATION_SPEC.md) |
| **08** | Penanganan Kegagalan & Recovery | [docs/02-architecture/FAILURE_MODES_AND_RECOVERY.md](file:///Users/nabilartanabil/SourceCode/AUTO-TRADE-AA/docs/02-architecture/FAILURE_MODES_AND_RECOVERY.md) |
| **09** | Kamus Data (21 Tabel) | [docs/04-data/DATA_DICTIONARY.md](file:///Users/nabilartanabil/SourceCode/AUTO-TRADE-AA/docs/04-data/DATA_DICTIONARY.md) |
| **10** | Diagram ERD Sistem | [docs/03-diagrams/ERD.mmd](file:///Users/nabilartanabil/SourceCode/AUTO-TRADE-AA/docs/03-diagrams/ERD.mmd) |
| **11** | Kontrol & Standar Keamanan | [docs/05-security/SECURITY_CONTROLS.md](file:///Users/nabilartanabil/SourceCode/AUTO-TRADE-AA/docs/05-security/SECURITY_CONTROLS.md) |
| **12** | SOP Circuit Breaker & Recovery | [docs/05-security/CIRCUIT_BREAKER_OPERATIONAL_SOP.md](file:///Users/nabilartanabil/SourceCode/AUTO-TRADE-AA/docs/05-security/CIRCUIT_BREAKER_OPERATIONAL_SOP.md) |
| **13** | Runbook Operasional Telegram Bot | [docs/05-security/TELEGRAM_BOT_SETUP_AND_RUNBOOK.md](file:///Users/nabilartanabil/SourceCode/AUTO-TRADE-AA/docs/05-security/TELEGRAM_BOT_SETUP_AND_RUNBOOK.md) |
| **14** | Live Trading Safety Gate (Fase 7) | [docs/05-security/LIVE_TRADING_SAFETY_GATE.md](file:///Users/nabilartanabil/SourceCode/AUTO-TRADE-AA/docs/05-security/LIVE_TRADING_SAFETY_GATE.md) |
| **15** | Matriks Ketertelusuran (RTM) | [docs/audit/REQUIREMENTS_TRACEABILITY_MATRIX.md](file:///Users/nabilartanabil/SourceCode/AUTO-TRADE-AA/docs/audit/REQUIREMENTS_TRACEABILITY_MATRIX.md) |

---

## 🔒 Kebijakan Keamanan & Regulasi

- **Tidak Ada Kustodi Private Key:** Platform tidak pernah meminta atau menyimpan private key dompet pengguna. Semua eksekusi didasarkan pada API Key bertanda tangan (*read/trade only*) tanpa izin penarikan (*no-withdrawal permission*).
- **Hard-Locked Paper Trading:** Parameter `LIVE_TRADING_ENABLED` terkunci pada `false`. Pengalihan ke mode live hanya diizinkan setelah kelulusan formal 5 gerbang keamanan pada [LIVE_TRADING_SAFETY_GATE.md](file:///Users/nabilartanabil/SourceCode/AUTO-TRADE-AA/docs/05-security/LIVE_TRADING_SAFETY_GATE.md).
- **Telegram Authorization Allowlist:** Hanya ID pengguna Telegram yang terdaftar pada variabel lingkungan yang dapat mengeksekusi instruksi kontrol. Pesan dari pengguna tidak dikenal diabaikan tanpa respon.