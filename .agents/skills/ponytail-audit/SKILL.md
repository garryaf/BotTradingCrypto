---
name: ponytail-audit
description: Audit kualitas seluruh repo seperti senior dev yang baru mewarisinya dan akan dipanggil saat rusak: bug, lubang keamanan, yang jebol saat beban nyata, kode berisiko tanpa test, jalur lambat, dan yang bisa dihapus/digabung/dipisah. Berperingkat, laporan sekali jalan, tidak mengubah kode.
---

# Ponytail Audit Skill

Audit seluruh repo seperti senior developer yang baru saja mewarisinya dan akan
dipanggil saat kode ini rusak. Urutan kepentingan: **correct, safe, holds under load,
tested, fast, lean**. Lean tetap penting: tiap baris tambahan harus dibaca, dites, dan
diperbaiki nanti. Ini laporan yang diminta user, jadi berikan lengkap. Skill ini
**tidak mengubah kode**.

## 1. Petakan dulu

- Audit apa yang user sebut: sebuah folder, sebuah package, atau seluruh repo. Tidak
  disebut: seluruh repo.
- Baca README, config deploy dan build, daftar dependency, entry point (main, routes,
  handler, job, perintah CLI), dan test.
- Temukan beban yang diharapkan: satu orang menjalankan script, atau banyak user dan
  proses sekaligus. Nilai skala terhadap itu, dan sebut beban yang diasumsikan.
- Telusuri alur utama ujung ke ujung: dari mana data masuk, apa yang disimpan, apa yang
  keluar. Baca jalur itu penuh: input user, uang, auth, write data, background job,
  apa pun yang dibagi antar proses.
- Repo besar: masuk dalam di mana kesalahan paling mahal, bukan file per file. Sebut
  bagian mana yang tidak dibaca.

## 2. Yang dicari

1. **Bug:** hasil salah, crash, edge case terlewat (kosong, nol, item terakhir,
   pembulatan, zona waktu), caller yang tidak sepakat dengan return fungsi, aturan sama
   diterapkan berbeda di dua tempat.
2. **Risk:** lubang keamanan (injection, randomness lemah, secret di kode, input user
   tanpa cek), kehilangan data (error ditelan, urutan write salah, tanpa transaksi).
3. **Scale:** aman untuk satu user, salah untuk banyak: race check-then-write, pekerjaan
   sama diulang tiap proses, memori/list yang hanya tumbuh, satu query per item, O(n^2)
   pada input besar, state per-proses yang seharusnya dibagi.
4. **Missing test:** logika berisiko (branch, parser, uang, keamanan, write data) tanpa
   test yang gagal saat ia rusak. Satu test bagus, bukan coverage.
5. **Speed:** perlambatan besar adalah masalah. Perbaikan kecil (kerja diulang di hot
   loop) adalah saran; sebagian software menghitung tiap milidetik.
6. **Lean:** kode yang tidak perlu ada atau bisa lebih kecil.
   - delete: dead code, opsi/flag/config tak terpakai, fitur spekulatif
   - reuse: dua helper melakukan hal sama (simpan satu, sebut path-nya)
   - stdlib/native: standard library atau platform sudah melakukannya; dependency untuk
     yang beberapa baris atau platform bisa
   - yagni: interface dengan satu implementasi, factory dengan satu produk, wrapper yang
     cuma meneruskan panggilan
   - merge: near-copy yang harus berubah bersama
   - split: satu fungsi/class mengerjakan beberapa job tak terkait. Pisah per job, bukan
     per jumlah baris.

## 3. Cek sebelum lapor

- Tiap temuan butuh kasus konkret: "input atau situasi ini menghasilkan hasil salah ini".
  Tanpa kasus, bukan temuan.
- Sebelum menyebut kode tak terpakai, `grep` seluruh tree termasuk test, fixture, config,
  dan referensi string/dinamis.
- Shortcut yang ditandai komentar `shortcut:` (atau `ponytail:` lama) yang menyebut
  batasnya adalah keputusan, bukan temuan, kecuali beban yang diharapkan sudah melewatinya.
- Usulkan perbaikan terkecil yang berhasil. Utamakan perbaikan yang menghapus kode. Jangan
  tambah layer, framework, atau config yang masalahnya tidak butuh.
- Tanpa selera gaya, tanpa "consider", tanpa kekhawatiran samar.

## 4. Output

Bahasa sangat sederhana: kalimat pendek, kata sehari-hari. Jelaskan istilah teknis saat
pertama dipakai. Pembaca mungkin belum pernah melihat kode ini.

Mulai dengan `What this repo does:` dalam dua-tiga kalimat, dan beban yang diasumsikan.

Lalu temuan dalam tiga grup, terpenting dulu, lewati grup kosong:
- **Must fix:** bug, keamanan, kehilangan data, rusak pada beban yang diharapkan.
- **Should fix:** kode berisiko tanpa test, lambat nyata, duplikasi, fungsi campur job,
  kode yang tidak perlu ada.
- **Nice to have:** percepatan kecil, bentuk lebih pendek.

Nomori temuan lintas semua grup, agar user bisa bilang "fix 2 dan 5". Maksimum 20 temuan;
bila ada yang lebih kecil dilewati, sebut berapa banyak. Tiap temuan punya empat bagian,
masing-masing satu-dua kalimat pendek:

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
- `Verdict:` satu baris: sehat, atau apa yang diperbaiki duluan.
- `Lean: -<N> lines, -<M> dependencies possible.` bila ada temuan lean.
- `Not checked:` bagian yang tidak dibaca atau tidak bisa dijalankan.

Tidak ada temuan: `What this repo does:`, lalu `Healthy. Nothing to fix.` dan satu baris
tentang apa yang dicek.

Skill ini laporan sekali jalan, **tidak mengubah kode**.
