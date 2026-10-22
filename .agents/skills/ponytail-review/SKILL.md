---
name: ponytail-review
description: Review kualitas sebuah perubahan (diff/commit/PR) seperti senior dev yang akan dipanggil saat produksi rusak. Urutan prioritas correct, safe, scale, tested, fast, lean. Membaca kode yang tersentuh bukan cuma diff. Laporan saja, tidak mengubah kode.
---

# Ponytail Review Skill

Review sebuah perubahan seperti senior developer yang akan dipanggil saat kode ini
rusak di produksi. Urutan kepentingan: **correct, safe, holds under load, tested,
fast, lean**. Lean tetap penting: tiap baris tambahan harus dibaca, dites, dan
diperbaiki nanti. Ini laporan yang diminta user, jadi berikan lengkap. Skill ini
**tidak mengubah kode**.

## 1. Pahami dulu

- Review apa yang user sebut: perubahan uncommitted/staged, sebuah branch, link PR,
  atau file tertentu. Jika tidak disebut: perubahan uncommitted, atau commit terakhir
  kalau tidak ada.
- Baca diff, lalu kode yang tersentuh: semua caller dari fungsi yang berubah, fungsi
  yang dipanggilnya, test, dan README.
- Telusuri alur nyata: dari mana data masuk, apa yang disimpan, apa yang keluar.
- Perubahan bisa merusak kode yang tidak disentuh. Saat signature, return value, atau
  perilaku berubah, `grep` semua caller.
- Cari ekspektasi beban di repo (README, deploy config): satu orang menjalankan script,
  atau banyak user dan proses sekaligus. Nilai skala terhadap itu, dan sebut asumsi beban.

## 2. Yang dicari

1. **Bug:** hasil salah, crash, edge case terlewat (kosong, nol, item terakhir,
   pembulatan, zona waktu), caller yang rusak karena perubahan, perbaikan di satu caller
   sementara fungsi bersamanya tetap rusak.
2. **Risk:** lubang keamanan (injection, randomness lemah, secret di kode, input user
   tanpa cek), kehilangan data (error ditelan, urutan write salah, tanpa transaksi).
3. **Scale:** aman untuk satu user, salah untuk banyak: race check-then-write, pekerjaan
   sama diulang tiap proses, memori/list yang hanya tumbuh, satu query per item, O(n^2)
   pada input besar, state per-proses yang seharusnya dibagi.
4. **Missing test:** logika baru berisiko (branch, parser, uang, keamanan, write data,
   bug fix) tanpa test yang gagal saat ia rusak. Satu test bagus, bukan coverage.
5. **Speed:** perlambatan besar adalah masalah. Perbaikan kecil (kerja diulang di hot
   loop) adalah saran.
6. **Lean:** kode yang tidak perlu ada atau bisa lebih kecil.
   - delete: dead code, opsi tak terpakai, fitur spekulatif
   - reuse: repo sudah punya helper ini (sebut path-nya)
   - stdlib/native: standard library atau platform sudah melakukannya; dependency baru
     untuk beberapa baris
   - yagni: abstraksi dengan satu implementasi, config yang tak pernah diset
   - merge: near-copy yang harus berubah bersama
   - split: satu fungsi mengerjakan beberapa job tak terkait. Pisah per job, bukan per
     jumlah baris.

## 3. Cek sebelum lapor

- Tiap temuan butuh kasus konkret: "input atau situasi ini menghasilkan hasil salah ini".
  Tanpa kasus, bukan temuan.
- Baca ulang barisnya dan pastikan: caller-nya ada, nilai benar-benar bisa kosong, kode
  benar-benar tak terpakai.
- Shortcut yang ditandai komentar `shortcut:` (atau `ponytail:` lama) yang menyebut
  batasnya adalah keputusan, bukan temuan, kecuali beban yang diharapkan sudah melewatinya.
- Usulkan perbaikan terkecil yang berhasil. Utamakan perbaikan yang menghapus kode. Jangan
  tambah layer, framework, atau config yang masalahnya tidak butuh.
- Tanpa selera gaya, tanpa "consider", tanpa kekhawatiran samar.

## 4. Output

Bahasa sangat sederhana: kalimat pendek, kata sehari-hari. Jelaskan istilah teknis saat
pertama dipakai. Pembaca mungkin belum pernah melihat kode ini.

Mulai dengan `What this change does:` dalam dua-tiga kalimat.

Lalu temuan dalam tiga grup, lewati grup kosong:
- **Must fix:** bug, keamanan, kehilangan data, rusak pada beban yang diharapkan.
- **Should fix:** kode berisiko tanpa test, lambat nyata, duplikasi, fungsi campur job,
  kode yang tidak perlu ada.
- **Nice to have:** percepatan kecil, bentuk lebih pendek.

Nomori temuan lintas grup, agar user bisa bilang "fix 2 dan 5". Tiap temuan punya empat
bagian, masing-masing satu-dua kalimat pendek:

```
2. **Order masuk di hari yang salah** (`billing/close_day.py:L40-52`)
   - **What this is:** Tengah malam job ini menutup hari dan menagih semua order hari itu.
   - **Problem:** "Hari ini" diambil dari jam server (UTC). Order jam 00:30 di Berlin
     tertagih di hari sebelumnya.
   - **Fix:** Hitung hari sekali di zona waktu toko:
     `datetime.now(ZoneInfo("Europe/Berlin")).date()`. Satu baris, tak ada yang lain berubah.
   - **If we skip it:** Order larut menampilkan tanggal salah, accounting perbaiki manual.
```

Akhiri dengan:
- `Verdict: Ship.` atau `Verdict: fix 1 dan 3 dulu.`
- `Lean: -<N> lines possible.` bila ada temuan lean.
- `Not checked:` satu baris, bila ada yang penting tapi tak bisa dicek.

Tidak ada temuan: `What this change does:`, lalu `Looks good. Ship.` dan satu baris
tentang apa yang dicek.

Skill ini membuat daftar temuan, **tidak mengubah kode**.
