# SPESIFIKASI UI/UX — KOMPONEN VISUAL INTERAKTIF DASHBOARD
**Dokumen:** `docs/01-requirements/UI_UX_SPECIFICATION.md`  
**Proyek:** AI Crypto Trading & Copy-Trading Platform (AUTO-TRADE-AA)  
**Versi:** 1.0.0 (Fase 5)  
**Status:** Draf Resmi Spesifikasi UI/UX  
**Referensi FR:** `FR-UI-01`, `FR-UI-02`, `FR-UI-03`  

---

## 1. Hierarki Halaman Dashboard

| Route | Komponen Halaman | Deskripsi |
|---|---|---|
| `/` | `frontend/src/app/page.tsx` | Dashboard utama: EquityHero, CandleChart, PositionsTable, TickerStrip |
| `/risk` | `frontend/src/app/risk/page.tsx` | Panel Risk Gate & Signal Log |
| `/wallets` | `frontend/src/app/wallets/page.tsx` | Wallet Explorer & Token List |

---

## 2. Sistem Warna & Token Visual

Semua token warna didefinisikan sebagai CSS custom properties dan Tailwind class:

| Token CSS / Tailwind | Nilai Hex/RGB | Digunakan Untuk |
|---|---|---|
| `--profit` / `text-profit` / `stroke-profit` | `rgb(61, 220, 132)` — hijau neon | PnL positif, Bull glow, sparkline naik |
| `--loss` / `text-loss` / `stroke-loss` | `rgb(255, 92, 92)` — merah coral | PnL negatif, Bear glow, sparkline turun |
| `text-text` | Putih/abu terang | Nilai netral (kas, posisi) |
| `text-text-faint` | Abu-abu redup | Label, heading sekunder |
| `bg-bg-panel` | Panel gelap | Latar kartu komponen |
| `border-border` | Border tipis abu | Batas antar kartu |

---

## 3. Komponen Maskot Bull/Bear

### 3.1 Aturan State — Kapan Bull, Kapan Bear

**Sumber keputusan:** [`EquityHero.tsx:87`](../../frontend/src/components/EquityHero.tsx#L87)

```typescript
const dailyProfit = data.daily_realized_pnl_usd >= 0;
```

| Kondisi | Maskot | Warna Glow | Kelas CSS |
|---|---|---|---|
| `daily_realized_pnl_usd >= 0` (termasuk $0.00) | 🐂 **Bull** | Hijau neon `rgb(61,220,132)` | `text-profit` |
| `daily_realized_pnl_usd < 0` | 🐻 **Bear** | Merah coral `rgb(255,92,92)` | `text-loss` |

> **Catatan:** Threshold adalah `daily_realized_pnl_usd` (Realized PnL hari kalender berjalan, bukan Unrealized). Data di-reset tiap tengah malam UTC via `portfolio_snapshots.daily_realized_pnl_usd`.

### 3.2 Komponen `ProfitLossMascot`

**File:** [`frontend/src/components/ProfitLossMascot.tsx`](../../frontend/src/components/ProfitLossMascot.tsx)  
**Props:** `{ positive: boolean }`

**Perilaku animasi (Framer Motion):**

| State | `initial` | `animate` | `exit` |
|---|---|---|---|
| Masuk (Bull) | `opacity:0, scale:0.4, rotate:-20°` | `opacity:1, scale:1, rotate:0°` | `opacity:0, scale:0.4, rotate:+20°` |
| Masuk (Bear) | `opacity:0, scale:0.4, rotate:+20°` | `opacity:1, scale:1, rotate:0°` | `opacity:0, scale:0.4, rotate:-20°` |
| Loop bounce | — | `y: [0, -7px, 0]` setiap 2.2 detik | — |
| Loop glow | — | `drop-shadow` berdenyut 4px→14px→4px setiap 2.2 detik | — |

**Transisi spring:**
```typescript
scale: { type: "spring", stiffness: 260, damping: 16 }
```

### 3.3 Aset SVG Maskot

#### `BullMascot` — Banteng Menyerang

**File:** [`frontend/src/components/mascots/BullMascot.tsx`](../../frontend/src/components/mascots/BullMascot.tsx)  
**ViewBox:** `0 0 220 220`  
**Fill:** `currentColor` (diwarisi dari class `text-profit`)

| Elemen Visual | Deskripsi |
|---|---|
| Kaki (2x) | Pilar kokoh meruncing ke bawah, bercabang dua (cloven hooves) |
| Tubuh | Bahu otot melebar, dada meruncing (`cx:110 cy:118`) |
| Telinga | Segitiga kecil di sisi kepala |
| Tanduk | Melengkung tajam ke atas, runcing (`path` kompleks) |
| Kepala | Elips agak merendah ke depan (`rx:42 ry:38`) |
| Alis | Garis hitam bold miring — ekspresi marah/semangat |
| Mata | Segitiga putih + pupil hitam kecil |
| Moncong | Elips lebih terang + 2 lubang hidung oval |
| Steam hidung | Path melengkung dari moncong — efek emosi menggebu |
| Highlight | Garis putih tipis diagonal di punggung (shine stroke) |

#### `BearMascot` — Beruang Murung

**File:** [`frontend/src/components/mascots/BearMascot.tsx`](../../frontend/src/components/mascots/BearMascot.tsx)  
**ViewBox:** `0 0 220 220`  
**Fill:** `currentColor` (diwarisi dari class `text-loss`)

| Elemen Visual | Deskripsi |
|---|---|
| Postur | Lebih besar/berat dari Bull, berdiri tegak |
| Ekspresi | Alis melengkung turun (sedih/lesu) |
| Telinga | Setengah lingkaran di atas kepala |

---

## 4. Komponen `PnlGlow`

**File:** [`frontend/src/components/PnlGlow.tsx`](../../frontend/src/components/PnlGlow.tsx)  
**Props:** `{ positive: boolean; intensity?: "lg" | "sm"; children: ReactNode }`

**Formula glow (3 layer):**

| Layer | Radius | Alpha | Tujuan |
|---|---|---|---|
| Layer 1 (inti) | `6px × scale` | `0.55` | Sumber cahaya |
| Layer 2 (tengah) | `16px × scale` | `0.36` | Difusi medium |
| Layer 3 (luar) | `32px × scale` | `0.22` | Halo ambient |

**Scale multiplier:** `intensity === "lg" ? 1.0 : 0.55`

**Animasi breathing:**
```typescript
textShadow: [glow(0.55), glow(1.0), glow(0.55)]
transition: { duration: 2.2, repeat: Infinity, ease: "easeInOut" }
```

Efek napas berjalan selaras dengan bounce dan glow drop-shadow maskot (durasi 2.2 detik yang sama).

---

## 5. Komponen `ProfitLossSplash`

**File:** [`frontend/src/components/ProfitLossSplash.tsx`](../../frontend/src/components/ProfitLossSplash.tsx)  
**Trigger:** Muncul **sekali saja** saat koneksi backend pertama kali berhasil (`data.connected` berubah dari `false → true`).

**Durasi:** 3.200ms, lalu auto-dismiss.

```typescript
// EquityHero.tsx:65-70
if (data?.connected && !hasShownSplash.current) {
  hasShownSplash.current = true;
  setShowSplash(true);
  const timer = setTimeout(() => setShowSplash(false), 3200);
}
```

**Kondisi tampilan:** Menggunakan `dailyProfit` (sama dengan maskot) untuk menentukan warna splash positif/negatif.

---

## 6. Komponen `CountUp`

**File:** [`frontend/src/components/CountUp.tsx`](../../frontend/src/components/CountUp.tsx)  
**Props:** `{ value: number; format: (n: number) => string }`

Menampilkan angka ekuitas dengan animasi count-up saat nilai berubah. Digunakan di `EquityHero` untuk nilai `equity_usd`.

---

## 7. Komponen `TickerStrip`

**File:** [`frontend/src/components/TickerStrip.tsx`](../../frontend/src/components/TickerStrip.tsx)  
**Sumber data:** [`frontend/src/lib/binance.ts`](../../frontend/src/lib/binance.ts) — WebSocket Binance Spot ticker stream.

Strip harga bergerak horizontal di bagian atas dashboard, menampilkan harga real-time pasangan yang dipantau.

---

## 8. Pola Data Real-Time (Polling)

**Utility:** `frontend/src/lib/api.ts` — hook `usePolling<T>(url, intervalMs)`

| Komponen | Endpoint | Interval Polling |
|---|---|---|
| `EquityHero` | `GET /api/v1/portfolio` | 5.000ms |
| `SignalLog` | `GET /api/v1/signals` | 5.000ms |
| `RiskGatePanel` | `GET /api/v1/risk` | 5.000ms |
| `TickerStrip` | Binance WebSocket | Real-time (event-driven) |

---

## 9. Responsivitas Layout

| Breakpoint | Layout Grid Stat Cards |
|---|---|
| Mobile (`< sm`) | 2 kolom (`grid-cols-2`) |
| Desktop (`≥ sm`) | 4 kolom (`sm:grid-cols-4`) |

---

## 10. Item yang Dilewati / Risiko

- **`BearMascot` tidak dibaca penuh** — inspeksi file menunjukkan 4.114 byte, dokumentasi elemen visual berdasarkan pattern yang sama dengan `BullMascot` + komentar file. Lakukan review langsung jika aset SVG Bear perlu diperbarui.
- **Threshold PnL berdasarkan Realized (bukan Unrealized)** — jika posisi besar belum ditutup, maskot bisa Bull meski floating loss signifikan. Pertimbangkan menambahkan `daily_unrealized_pnl_usd` ke threshold jika diperlukan di iterasi berikutnya.
