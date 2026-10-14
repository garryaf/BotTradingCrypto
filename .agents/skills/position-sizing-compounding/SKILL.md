---
name: position-sizing-compounding
description: Keahlian kalkulasi ukuran posisi berbasis risiko 0.5% ekuitas, compounding adaptif, manajemen partial take profit, dan trailing stop.
---

# Position Sizing & Compounding Skill

Gunakan skill ini untuk menghitung kuantitas order secara matematis, mengelola reinvestasi keuntungan (*compounding*), dan mengatur level manajemen posisi dinamis (**Kotak 4 & 5**).

## 1. Rumus Kuantitatif Position Sizing

Ukuran posisi (*position size*) **bukan** persentase modal yang dibeli, melainkan besaran nominal yang dikalibrasi agar jika Stop Loss terkena, kerugian tepat sebesar **0.5% dari ekuitas terkini**:

$$\text{Dollar Risk} = \text{Current Equity} \times 0.005$$

$$\text{Risk per Unit} = |\text{Entry Price} - \text{Stop Loss Price}|$$

$$\text{Position Size (Lots/Tokens)} = \frac{\text{Dollar Risk}}{\text{Risk per Unit}}$$

$$\text{Total Capital Required} = \text{Position Size} \times \text{Entry Price}$$

*Catatan Kritis:* Jika $\text{Total Capital Required}$ melebihi saldo kas yang tersedia, ukuran posisi dipotong sesuai saldo kas maksimum tanpa melanggar batas risiko 0.5%.

## 2. Compounding Adaptif (Adaptive Compounding Rules)

1. **Reinvest Profit ke Modal:**
   - Setelah transaksi profit ditutup, ekuitas portofolio meningkat.
   - Sizing pada transaksi berikutnya secara otomatis menggunakan basis ekuitas baru yang lebih besar (pertumbuhan eksponensial dengan risiko terkontrol).
2. **Pengurangan Risiko Adaptif saat Drawdown:**
   - Jika portofolio mengalami drawdown $\ge 3.0\%$ dari High-Water Mark:
     - Turunkan toleransi risiko per trade dari **0.5%** menjadi **0.35%**.
   - Jika drawdown $\ge 5.0\%$:
     - Turunkan toleransi risiko per trade menjadi **0.25%**.
   - Risiko dikembalikan ke standar normal 0.5% hanya setelah ekuitas berhasil mencetak High-Water Mark baru.

## 3. Manajemen Posisi: Partial TP & Trailing Stop

- **Take Profit 1 (TP1):**
  - Level: Rasio Risk:Reward 1:1.5 ($1.5 \times R$).
  - Aksi: Jual 50% dari total posisi (*Partial Take Profit*).
  - Pindahkan Stop Loss ke titik impas (*Breakeven / Entry Price*).
- **Take Profit 2 (TP2):**
  - Level: Rasio Risk:Reward 1:3.0 ($3.0 \times R$).
  - Aksi: Jual sisa 50% posisi.
- **Trailing Stop (Opsional pada Rezim Strong Trend):**
  - Mengunci keuntungan menggunakan indikator ATR (misal: $2.0 \times \text{ATR}$ di bawah harga tertinggi candle terakhir).

## 4. Format Output Perhitungan Sizing

```json
{
  "symbol": "BTCUSDT",
  "current_equity_usd": 10245.32,
  "max_dollar_risk": 51.23,
  "entry_price": 64200.0,
  "stop_loss": 63400.0,
  "risk_per_unit": 800.0,
  "calculated_position_size": 0.06403,
  "total_order_value_usd": 4110.72,
  "partial_tp1_price": 65400.0,
  "partial_tp2_price": 66600.0,
  "compounding_multiplier": 1.0
}
```
