---
name: risk-gate-validation
description: Keahlian AI agent dan aturan deterministik untuk memvalidasi kepatuhan risiko mutlak sebelum eksekusi (Risk 0.5%, Daily Loss 2%, Drawdown 8%, Expectancy Positif).
---

# Risk Gate Validation Skill

Gunakan skill ini untuk menguji apakah usulan order perdagangan mematuhi gerbang keselamatan deterministik (**Kotak 3 - RISK GATE**). Jika salah satu kriteria gagal, status akhir wajib berupa **NO TRADE**.

## 1. Kriteria Pemeriksaan Wajib (Checklist 9 Pintu)

| Pintu Risiko | Parameter Ambang Batas | Kondisi Gagal (Reject) |
|---|---|---|
| **1. Expectancy Positif** | $E = (\text{WinRate} \times \text{AvgWin}) - (\text{LossRate} \times \text{AvgLoss}) - \text{TotalFees} > 0$ | $E \le 0$ (Strategi tidak memiliki keunggulan matematis bersih dari biaya). |
| **2. Risk per Trade** | **Maksimum 0.5% dari Total Equity Terkini**. Nominal risiko: $\text{Equity} \times 0.005$. | Risiko yang dihitung melebihi 0.5% ekuitas. |
| **3. Daily Loss Limit** | **Maksimum 2.0% penurunan ekuitas dalam 24 jam**. | Kerugian hari berjalan $\ge 2.0\%$ ekuitas pembukaan. |
| **4. Drawdown Limit** | **Maksimum 8.0% dari High-Water Mark portofolio**. | Drawdown akumulatif $\ge 8.0\%$. Memicu Circuit Breaker pembekuan strategi. |
| **5. Cek Spread & Likuiditas** | Spread bid-ask $\le 0.08\%$; Kedalaman orderbook 2% $\ge \$50.000$ USD. | Spread lebar atau likuiditas dangkal yang memicu slippage tinggi. |
| **6. Validasi Stop Loss** | Stop Loss **WAJIB ADA** dan terdefinisi secara numerik di level logis pasar. | Order tanpa Stop Loss atau jarak SL melebihi toleransi risiko 0.5%. |
| **7. Cek Saldo & Lot Size** | Ukuran lot harus memenuhi `min_lot_size` dan `tick_size` exchange (Binance Spot / Solana AMM). | Saldo kas tidak mencukupi untuk memenuhi lot minimum. |
| **8. Tidak Melanggar Aturan** | Jumlah posisi terbuka simultan tidak melebihi batas (maks 3-5 posisi). | Melebihi kuota posisi terbuka. |
| **9. Market Condition OK** | Status pasar tidak dalam kondisi anomali ekstrem atau flash-crash; latency feed data normal. | Feed harga mengalami keterlambatan (*stale* > 30 detik). |

## 2. Aturan Keputusan (Decision Flow)

```
        [ Input Signal + Portofolio State ]
                        │
                        ▼
            [ Evaluasi 9 Pintu Risiko ]
                        │
         ┌──────────────┴──────────────┐
         ▼ (Semua Pintu Terpenuhi)     ▼ (Ada 1 Pintu Gagal)
  [ STATUS: LOLOS RISK GATE ]    [ STATUS: NO TRADE ]
   - Teruskan ke Execution Engine - Batalkan sinyal
   - Catat status PASSED          - Catat alasan spesifik di log audit
```

## 3. Format Output Evaluasi

```json
{
  "signal_id": "sig-binance-20261014-001",
  "passed_risk_gate": true,
  "calculated_risk_pct": 0.5,
  "allocated_risk_usd": 51.22,
  "current_daily_loss_pct": 0.45,
  "current_drawdown_pct": 2.10,
  "rejection_reasons": [],
  "execution_permission": "ALLOWED"
}
```
