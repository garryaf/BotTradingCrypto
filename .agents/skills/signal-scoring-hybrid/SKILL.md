---
name: signal-scoring-hybrid
description: Keahlian AI agent untuk menyintesis sinyal perdagangan hibrida (Trend Following, Momentum Breakout, Mean Reversion), menghitung estimasi winrate, dan menyaring sinyal palsu.
---

# Signal Scoring & Hybrid Strategy Skill

Gunakan skill ini untuk menyintesis data indikator teknikal multi-timeframe dan data pasar menjadi skor probabilitas sinyal perdagangan yang terukur.

## 1. Tiga Pilar Strategi Hibrida

1. **Trend Following (TF):**
   - Mengikuti arah tren utama H4/D1. Entry saat pullback ke dynamic support (EMA 20/50 atau VWAP).
   - Validasi: Volume konfirmasi meningkat saat harga memantul.
2. **Momentum Breakout (MB):**
   - Menembus level kunci Support/Resistance atau chart pattern (Cup & Handle, Flag, Range High).
   - Validasi: Candle breakout ditutup di luar level dengan volume > 1.5x volume rata-rata 20 candle.
3. **Mean Reversion (MR):**
   - Beli saat harga oversold di support terkuat pada kondisi pasar Sideways (RSI < 30, harga di lower Bollinger Band).
   - Validasi: ADX harus < 20 (bukan dalam strong trend).

## 2. Penyaringan Sinyal Palsu (False Signal Filters)

Sebelum mengeluarkan sinyal `BUY`, periksa 4 filter eliminasi sinyal palsu:
- [x] **Filter Likuiditas & Spread:** Spread bid-ask tidak boleh lebih dari 0.1% dari harga spot.
- [x] **Filter Volume Divergence:** Jika harga membuat High baru tetapi volume menurun drastis, tolak sinyal breakout (*bearish divergence*).
- [x] **Filter Overextended:** Jika RSI > 75 pada timeframe H1, jangan lakukan buy momentum; tunggu pullback.
- [x] **Filter Multi-Timeframe Alignment:** Arah sinyal pada timeframe kecil (M5/M15) tidak boleh berlawanan dengan arah tren besar (H4).

## 3. Rumus Pembobotan Skor Keyakinan (Confidence Score)

$$\text{Confidence Score} = (0.35 \times S_{\text{trend}}) + (0.30 \times S_{\text{volume}}) + (0.20 \times S_{\text{pattern}}) + (0.15 \times S_{\text{rr\_ratio}})$$

Ambang Batas Kelulusan:
- Skor $\ge 0.75$: Sinyal **VALID / HIGH PROBABILITY**. Diteruskan ke Risk Gate.
- Skor $< 0.75$: Sinyal **INVALID / WEAK**. Status: `NO_TRADE`.

## 4. Format Output Terstruktur Sinyal

```json
{
  "signal_id": "sig-binance-20261014-001",
  "symbol": "SOLUSDT",
  "strategy_type": "MOMENTUM_BREAKOUT",
  "action": "BUY",
  "entry_price": 152.40,
  "stop_loss": 149.35,
  "take_profit_1": 156.98,
  "take_profit_2": 161.55,
  "estimated_winrate_pct": 62.5,
  "confidence_score": 0.84,
  "risk_reward_ratio": 2.0,
  "rationale": "Breakout resistance 152.00 terkonfirmasi volume 2x rata-rata dan H4 trend bullish."
}
```
