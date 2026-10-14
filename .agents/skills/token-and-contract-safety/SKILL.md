---
name: token-and-contract-safety
description: Keahlian AI agent untuk mengaudit keamanan smart contract SPL token Solana dan memvalidasi aturan simbol pasar Bybit Spot.
---

# Token and Contract Safety Skill

Gunakan skill ini untuk memeriksa integritas aset kripto sebelum diizinkan masuk ke pipeline analisis sinyal dan eksekusi.

## 1. Audit Keamanan Smart Contract (Solana SPL Token)

Sebelum mempertimbangkan token di jaringan Solana, periksa 5 parameter wajib:
1. **Freeze Authority:**
   - Kondisi Aman: `freeze_authority == null` (Otoritas telah dicabut secara permanen).
   - Kondisi Bahaya: Jika masih ada alamat pemegang otoritas pembekuan, aset diklasifikasikan sebagai **CRITICAL RISK (POTENTIAL HONEYPOT)** -> **TOLAK SEGERA**.
2. **Mint Authority:**
   - Kondisi Aman: `mint_authority == null` (Pencetakan token baru telah dinonaktifkan).
   - Kondisi Bahaya: Jika dev masih bisa mencetak token tak terbatas -> **TOLAK**.
3. **Likuiditas Kolam AMM (LP Status):**
   - Kondisi Aman: Minimal 95% - 100% LP token telah di-*burn* atau dikunci (*locked*) di protokol terpercaya (Streamflow/uncx).
4. **Konsentrasi Pasokan (Top 10 Holders):**
   - Kondisi Aman: Total kepemilikan 10 wallet terbesar (di luar pool DEX) $\le 20\%$ dari total suplai yang beredar.
5. **Usia Kolam Likuiditas:**
   - Waktu pembuatan pool minimal $\ge 24$ jam untuk menghindari manipulasi sniper detik awal.

## 2. Validasi Simbol Pasar (Bybit Spot Rules)

Untuk instrumen spot bursa terpusat (Bybit Spot):
1. **Status Simbol:** `status == "Trading"` (Bukan dalam status suspend atau delisting).
2. **Likuiditas & Volume Minimum:** Volume transaksi 24 jam pasangan trading harus $\ge \$1.000.000$ USD.
3. **Kepatuhan Precision:**
   - Validasi `tick_size` (misal 0.01) untuk harga order.
   - Validasi `min_order_qty` dan `lot_size` (misal 0.001) untuk kuantitas order.
4. **Maksimum Spread:** Spread selisih Bid teratas dan Ask teratas tidak boleh melebihi 0.08%.

## 3. Format Output Evaluasi Keamanan

```json
{
  "asset_identifier": "SOLUSDT",
  "venue_type": "BYBIT_SPOT",
  "contract_safety_score": 98.0,
  "risk_classification": "SAFE_FOR_TRADING",
  "checks_passed": {
    "freeze_authority_revoked": true,
    "mint_authority_revoked": true,
    "liquidity_depth_adequate": true,
    "spread_within_limits": true,
    "trading_status_active": true
  },
  "verdict": "APPROVED"
}
```
