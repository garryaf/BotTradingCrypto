# 17 — F-17: Validasi Rasio Risk:Reward (R:R ≥ 1:1.5) pada Risk Gate

**Tanggal:** 2026-10-28
**Komponen:** `backend/src/risk/gate.py`, `backend/src/risk/engine.py`, `backend/src/config.py`, `backend/src/risk/test_gate.py`, `backend/src/risk/test_parity.py`, `engine/src/main.rs`
**Status F-17:** **RESOLVED** (Selesai dan Terverifikasi)

---

## 1. Latar Belakang & Masalah (Root Cause)

Berdasarkan `docs/01-requirements/FUNCTIONAL_REQUIREMENTS.md` baris 106 (FR-RSK-01):
> *"Stop Loss wajib terdefinisi secara numerik dan rasio Risk:Reward ≥ 1:1.5"*

Pada implementasi sebelumnya:
1. Pintu 6 (`stop_loss_check`) di `backend/src/risk/gate.py` dan `engine/src/main.rs` hanya memverifikasi keberadaan numerik stop-loss (`stop_loss > 0`), perbedaan harga (`stop_loss != entry_price`), dan arah posisi (`stop_loss < entry_price` untuk `BUY` atau `stop_loss > entry_price` untuk `SELL`).
2. Ambang batas rasio Risk:Reward minimal $1:1.5$ sama sekali belum dievaluasi di Pintu 6. Akibatnya, sinyal trading dengan target profit yang terlalu tipis (misal: R:R = 1.0) dapat lolos jika probabilitas estimasi winrate cukup tinggi untuk menghasilkan *expectancy* positif di Pintu 1.

---

## 2. Keputusan Desain & Batasan

1. **Basis Pengukuran R:R = TP1 (Conservative First Target):**
   - Rasio Risk:Reward dihitung secara deterministik terhadap target parsial pertama:
     $$\text{risk\_unit} = |\text{entry\_price} - \text{stop\_loss}|$$
     $$\text{tp1\_distance} = |\text{take\_profit\_1} - \text{entry\_price}|$$
     $$\text{rr\_ratio} = \frac{\text{tp1\_distance}}{\text{risk\_unit}} \ge 1.5$$
   - Hal ini selaras dengan dokumentasi strategi (`.agents/skills/position-sizing-compounding/SKILL.md` dan `backend/src/backtest/strategy.py:TP1_R = 1.5`).
2. **Pesan Penolakan Eksplisit:**
   - Sinyal dengan R:R < 1.5 ditolak dengan alasan penolakan baru: `"INSUFFICIENT_RISK_REWARD"`.
   - Jika stop-loss tidak valid/hilang, penolakan tetap `"INVALID_STOP_LOSS"` tanpa *double-flagging* semu.
3. **Single Source of Truth Konfigurasi:**
   - Ditambahkan `min_risk_reward_ratio: Decimal = Decimal("1.5")` pada `backend/src/config.py`.
   - `backend/src/risk/engine.py` (`risk_limits()`) mengirimkan parameter `"min_risk_reward_ratio": 1.5` ke Rust engine dalam payload `SignalCandidate.limits`.
   - Rust engine (`engine/src/main.rs`) menerima field `min_risk_reward_ratio` dalam struct `Limits` dengan default fallback `1.5`.

---

## 3. Implementasi yang Diterapkan

### A. Python Risk Gate (`backend/src/risk/gate.py`)
- Pintu 6 diperbarui untuk mengevaluasi `sl_present` terlebih dahulu, lalu menghitung jarak R:R terhadap `settings.min_risk_reward_ratio`:
  ```python
  direction_ok = (action == "BUY" and stop_loss < entry_price) or (action == "SELL" and stop_loss > entry_price)
  sl_present = stop_loss > 0 and stop_loss != entry_price and direction_ok
  if not sl_present:
      reasons.append("INVALID_STOP_LOSS")

  if sl_present:
      risk_unit = abs(entry_price - stop_loss)
      rr_ok = risk_unit > 0 and abs(take_profit_1 - entry_price) >= settings.min_risk_reward_ratio * risk_unit
      if not rr_ok:
          reasons.append("INSUFFICIENT_RISK_REWARD")
  else:
      rr_ok = False

  stop_loss_check = sl_present and rr_ok
  ```
- Evaluasi sizing, balance/lot, dan expectancy tetap dapat dihitung jika `sl_present == True` tanpa cascading error semu, sementara hasil akhir gate menolak sinyal jika R:R tidak mencukupi.

### B. Rust Risk Engine (`engine/src/main.rs`)
- Menambahkan `fn d_min_risk_reward_ratio() -> f64 { 1.5 }`.
- Struct `Limits` ditambahkan `min_risk_reward_ratio: f64` (serde default + `Default` trait).
- `evaluate_candidate` di Rust mengimplementasikan logika ekuivalen:
  ```rust
  let min_rr = lim.min_risk_reward_ratio;
  let rr_ok = if sl_present {
      let risk_unit = (candidate.target_entry_price - candidate.suggested_stop_loss).abs();
      let tp1_dist = (candidate.suggested_take_profit_1 - candidate.target_entry_price).abs();
      let ok = risk_unit > 0.0 && tp1_dist >= min_rr * risk_unit;
      if !ok {
          reasons.push("INSUFFICIENT_RISK_REWARD".to_string());
      }
      ok
  } else {
      false
  };
  let stop_loss_ok = sl_present && rr_ok;
  gates.insert("stop_loss_check".to_string(), stop_loss_ok);
  ```

### C. Engine Client & Parity Contract (`backend/src/risk/engine.py` & `test_parity.py`)
- `risk_limits()` memasukkan `"min_risk_reward_ratio": float(settings.min_risk_reward_ratio)` sehingga Rust engine selalu membaca batas tunggal dari konfigurasi.
- `CASES` di `test_parity.py` ditambahkan kasus uji paritas `"rr_below_minimum"`.

---

## 4. Hasil Pengujian & Bukti Runtime

1. **Python Risk Gate Tests (`backend/src/risk/test_gate.py`):**
   - `test_insufficient_rr_rejected`: Sinyal dengan entry=100, SL=95, TP1=105 (R:R = 1.0) tertolak dengan alasan eksklusif `["INSUFFICIENT_RISK_REWARD"]` dan `stop_loss_check is False`.
   - `test_exact_minimum_rr_passes`: Sinyal dengan entry=100, SL=95, TP1=107.5 (R:R = 1.5 tepat ambang) lolos seluruh 9 pintu.
   - `test_rr_check_without_stop_loss_does_not_double_reject`: Stop loss tidak valid hanya menghasilkan `INVALID_STOP_LOSS` tanpa menduplikasi alasan `INSUFFICIENT_RISK_REWARD`.
   - Hasil: 19 test cases lulus `ok`.
2. **Rust Engine Cargo Unit Tests (`engine/src/main.rs`):**
   - `test_rr_below_minimum_rejected`: `candidate.suggested_take_profit_1 = 155.0` (1.0R) tertolak `INSUFFICIENT_RISK_REWARD`. Lulus `ok`.
   - `test_exact_rr_passes`: `candidate.suggested_take_profit_1 = 157.5` (1.5R) lolos gate. Lulus `ok`.
   - `test_missing_limits_json_falls_back_to_defaults`: Nilai default `min_risk_reward_ratio == 1.5` diverifikasi saat payload tidak mengirim field limits. Lulus `ok`.
3. **Rust Release Binary:**
   - `cargo build --release` berhasil mengompilasi binary `auto-trade-engine`.
4. **Regresi Suite:**
   - Semua modul backend (`test_gate`, `test_heuristics`, `test_copy_trade`, `test_solana_dex`, `test_ledger`, `test_wallet_scorer`, `test_anti_manipulation`) lulus 100% tanpa regresi.

