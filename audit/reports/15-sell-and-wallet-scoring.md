# 15 — F-27 (Hermes SELL) dan F-29/F-30 (scoring wallet)

**Tanggal:** 2026-10-26
**Dasar:** persetujuan pemilik ("saya setuju") atas keputusan terbuka di laporan 14 §5. Karena pesan itu tidak memilih opsi, saya mengambil opsi paling konservatif dan mencatatnya di sini; semuanya mudah dibalik.

## 1. Keputusan yang diterapkan
| Butir | Keputusan | Alasan / dokumen |
|---|---|---|
| Hermes SELL (F-27) | Opsi (a): Hermes **membuang** keputusan SELL sebelum membuat `TradingSignal` (dicatat di log; jawaban LLM tetap ada di `llm_requests`) | Paper trading spot hanya long; tidak ada dokumen yang menyebut short. Opsi (b) "SELL = tutup long" berarti exit digerakkan LLM, belum disetujui |
| Basis PnL wallet (F-29) | **SOL** | Jumlah di observasi adalah delta saldo SOL (`ingestion/solana.py`); `AI_AGENT_ARCHITECTURE.md` memakai `net_pnl_sol` |
| Definisi drawdown wallet (F-29) | `(HWM − ekuitas) / HWM` atas ekuitas terealisasi; modal = SOL minimum yang mampu mendanai trade yang teramati | Rumus MDD di `TESTING_PLAN.md` §5.5; modal wallet sebenarnya tidak diketahui |
| Spread/biaya DEX | **Tidak diubah**: sinyal copy-trade SPL tetap ditolak (fail-closed) | Butuh angka batas biaya dari pemilik; tidak saya karang |

## 2. Perubahan
- `agents/hermes.py`: SELL di-drop (+ log). Tidak ada lagi produsen sinyal entry SELL (copy-trade sudah `SELL_NOT_MIRRORED`).
- `agents/wallet_scorer.py`:
  - MDD dihitung dari kurva PnL terealisasi (sebelumnya dari jumlah nilai trade yang tidak pernah turun → selalu 0).
  - Fee tidak dikurangi dua kali: delta saldo SOL sudah memuat gas dan fee pool; konversi fee tetap $150 dihapus. Cabang `price_usd` dihapus (kolom itu tidak pernah diisi ingestion, dan satuannya USD).
  - **F-30 (baru):** SELL tanpa BUY teramati (token dibeli sebelum riwayat yang diambil) tidak lagi dihitung sebagai trade untung penuh.
  - Wallet tanpa trade tertutup tidak lagi mendapat 30 poin drawdown gratis.
- UI `WalletExplorer`: kolom "Net PnL (SOL)" tanpa "$". Kolom DB `net_pnl_usd` tetap (isinya SOL, didokumentasikan di `DATA_DICTIONARY.md`) agar tidak perlu migrasi.

## 3. Bukti
Test baru dijalankan juga terhadap kode lama (salinan sementara dari `HEAD`) dan **gagal** di sana:

| Test | Kode lama | Kode baru |
|---|---|---|
| `test_cycle_drops_sell_entry` | SELL menjadi `TradingSignal` | SELL tidak disimpan; BUY tetap tersimpan |
| `test_drawdown_from_realized_equity` (rugi, rugi, untung) | MDD 0.00, skor 56.13 | MDD 28.57, skor 39.11, PnL 0.1000 SOL |
| `test_losing_trader_metrics` (satu rugi 1000 → 400) | MDD 0.00, skor 30.00 | MDD 60.00, skor 0.00 |
| `test_sell_without_observed_buy_is_not_scored` | 1 SELL saja → menang 100%, skor **100.00** (lolos promosi) | 0 trade, skor 0.00 |

| Suite | Hasil |
|---|---|
| `bash scripts/run_integration_tests.sh` | 8/8 `ok` (rantai copy-trade: wallet kuat tetap ≥ 70 dan dipromosikan, wallet lemah < 70) |
| 14 self-check backend | 14/14 `ok` |
| `npm run lint` · `npm run test:e2e` | bersih · 9/9 |
| `cargo test` | tidak dijalankan ulang (engine tidak diubah; parity lewat image lulus) |

## 4. Masih terbuka
1. **Batas biaya DEX** — tanpa angka maksimum biaya round-trip per trade DEX, semua sinyal copy-trade SPL tetap ditolak gerbang spread.
2. **F-31:** rumus skor di kode berbeda dari Q-05 yang APPROVED (`0.4×Net PnL + 0.3×PF − 0.3×MDD`, umur wallet ≥ 30 hari). Rumus Q-05 mencampur satuan (SOL, rasio, %) sehingga tidak bisa dibandingkan dengan ambang 70. Perlu keputusan: ubah Q-05 mengikuti rumus kode, atau definisikan suku Net PnL yang dinormalisasi.
3. Batas yang diketahui (shortcut di kode): leg swap selain SOL (mis. USDC) dihitung 0 SOL; FR-WLT-01 kini ⚠️ karena durasi kepemilikan dan riwayat ≥ 30 hari belum ada.
