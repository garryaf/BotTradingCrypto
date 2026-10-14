---
name: market-regime-detection
description: Keahlian AI agent untuk mendeteksi rezim pasar kripto (Trending vs Sideways), menghitung volatilitas dan likuiditas dengan indikator teknikal (EMA, RSI, MACD, ATR, VWAP).
---

# Market Regime Detection Skill

Gunakan skill ini untuk menganalisis data pasar multi-timeframe dan mengklasifikasikan rezim pasar secara objektif sebelum menghasilkan sinyal perdagangan.

## 1. Klasifikasi Rezim Pasar (Market Regimes)

### A. Trending Bullish (Kuat)
- **Kondisi:**
  - Harga > EMA 20 > EMA 50 > EMA 200 pada timeframe H1 dan H4.
  - RSI (14) berada di rentang 55 - 70 (momentum sehat tanpa overbought ekstrem).
  - MACD histogram positif dan berada di atas garis sinyal.
  - ADX (Average Directional Index) > 25 (menunjukkan tren kuat).
- **Tindakan Strategi:** Utamakan sinyal **Trend Following (Long/Buy)** atau **Momentum Breakout**. Hindari Mean Reversion berlawanan tren.

### B. Trending Bearish (Kuat)
- **Kondisi:**
  - Harga < EMA 20 < EMA 50 < EMA 200 pada timeframe H1 dan H4.
  - RSI (14) berada di rentang 30 - 45.
  - MACD histogram negatif.
  - ADX > 25.
- **Tindakan Strategi:** Hindari pembelian spot baru; cari titik exit posisi atau tunggu konfirmasi pembalikan arah.

### C. Sideways / Range-Bound (Konsolidasi)
- **Kondisi:**
  - Harga berosilasi di sekitar EMA 50 dan VWAP.
  - ADX < 20 (tren lemah / ketiadaan arah).
  - Bollinger Bands menyempit (*squeeze*).
  - RSI berosilasi antara 40 dan 60.
- **Tindakan Strategi:** Aktifkan **Mean Reversion** (Beli di Support, Jual di Resistance). Nonaktifkan strategi Breakout karena tingginya risiko *fakeout*.

### D. Volatile High-Risk (Anomali)
- **Kondisi:**
  - ATR (14) melonjak > 2x lipat dari rata-rata 30 periode.
  - Spread bid-ask melebar signifikan.
- **Tindakan Strategi:** Rekomendasikan status **NO TRADE / WAIT** sampai volatilitas mereda.

## 2. Format Keluaran Terstruktur (JSON Output)

Saat skill ini dipanggil, kembalikan hasil dalam format JSON terkompresi:
```json
{
  "symbol": "BTCUSDT",
  "regime": "TRENDING_BULLISH",
  "adx_strength": 28.4,
  "volatility_state": "NORMAL",
  "recommended_strategy_type": "TREND_FOLLOWING",
  "confidence": 0.85
}
```
