# PONYTAIL SKILLS — GAP & TASK LIST
**Proyek:** AUTO-TRADE-AA
**Dokumen:** `docs/audit/PONYTAIL_SKILLS_GAP_TASKS.md`
**Status:** READ-ONLY — tasks saja, belum ada perubahan kode
**Tanggal:** 21 Oktober 2026
**Sumber:** repo `DietrichGebert/ponytail` (branch `main`) + source code lokal

---

## 1. Ringkasan

Ponytail versi lengkap punya dua command utama, `/ponytail-review` dan `/ponytail-audit`,
yang di repo upstream berbentuk skill (`skills/ponytail-review/SKILL.md`,
`skills/ponytail-audit/SKILL.md`).

Di project ini yang terpasang baru **ruleset always-on** (`.kiro/steering/ponytail.md`,
global + workspace). Dua command tersebut **belum ada** dalam bentuk apa pun yang bisa
dijalankan di sini.

Kenapa: Kiro adalah host "instruction-only" untuk ponytail — menurut INSTALL.md upstream,
Kiro memuat ruleset always-on **tanpa** slash-command/skill. Jadi di Kiro,
`/ponytail-review` dan `/ponytail-audit` tidak bisa dipanggil sebagai command; yang bisa
dilakukan adalah menyediakan workflow-nya sebagai skill lokal (`.agents/skills/`) atau
dokumen prosedur yang dijalankan manual oleh agent.

Catatan: 5 skill domain-trading yang sudah ada (`market-regime-detection`,
`position-sizing-compounding`, `risk-gate-validation`, `signal-scoring-hybrid`,
`token-and-contract-safety`) tidak terpengaruh — ini murni soal menambah dua workflow QA.

### Yang sudah ada vs belum
| Item | Upstream | Project ini | Status |
|------|----------|-------------|--------|
| Ruleset always-on | `.kiro/steering/ponytail.md` | ada (global + workspace) | ✅ Terpasang |
| `/ponytail-review` | `skills/ponytail-review/SKILL.md` | — | ❌ Belum |
| `/ponytail-audit` | `skills/ponytail-audit/SKILL.md` | — | ❌ Belum |
| `/ponytail-debt`, `-gain`, `-help`, band | skills/statusline | — | ❌ Belum (opsional, lihat PT-4) |

---

## 2. Daftar Task

### PT-1 (P1) — Pasang workflow `ponytail-review` sebagai skill lokal ✅ DONE
- **Kategori:** G. Technical / QA tooling
- **Gap:** Tidak ada prosedur review perubahan (diff) yang baku di project. Upstream
  `skills/ponytail-review/SKILL.md` mendefinisikannya; belum disalin ke sini.
- **Deliverable:** `.agents/skills/ponytail-review/SKILL.md` — adaptasi dari skill upstream,
  mengikuti format `SKILL.md` yang sudah dipakai 5 skill lain di `.agents/skills/`.
- **Isi wajib (dari sumber):** review berdasarkan urutan prioritas correct → safe → scale →
  tested → fast → lean; baca kode yang tersentuh bukan cuma diff; grep semua caller saat
  signature/return berubah; output 3 grup (Must fix / Should fix / Nice to have) dengan 4
  bagian per temuan (What this is / Problem / Fix / If we skip it); diakhiri `Verdict:`.
- **Acceptance:** file ada, lolos format SKILL.md, tidak mengubah kode produksi apa pun.

### PT-2 (P1) — Pasang workflow `ponytail-audit` sebagai skill lokal ✅ DONE
- **Kategori:** G. Technical / QA tooling
- **Gap:** Tidak ada prosedur audit seluruh repo yang baku. Upstream
  `skills/ponytail-audit/SKILL.md` mendefinisikannya; belum disalin.
- **Deliverable:** `.agents/skills/ponytail-audit/SKILL.md` — adaptasi dari skill upstream.
- **Isi wajib (dari sumber):** map repo dulu (README, deploy/build config, dependency,
  entry points, test); tentukan expected load dan sebut asumsinya; telusuri alur data
  end-to-end; cek bug/risk/scale/missing-test/speed/lean; output 3 grup bernomor, maks 20
  temuan; diakhiri `Verdict:`, `Lean: -N lines ...`, dan `Not checked:`.
- **Acceptance:** file ada, lolos format SKILL.md, tidak mengubah kode produksi apa pun.

### PT-3 (P2) — Discovery skill & cara memanggil ✅ DONE
- **Kategori:** C. Consistency
- **Temuan discovery:** Loader satu-satunya adalah `backend/src/agents/skills.py`:
  `load_skill_prompt(name)` membaca `.agents/skills/<name>/SKILL.md` **by convention** —
  tidak ada registry/enum/daftar tetap. Skill baru otomatis "terdaftar" begitu foldernya
  ada. Jadi `ponytail-review` dan `ponytail-audit` sudah bisa ditemukan tanpa perubahan kode.
- **Catatan penting:** `load_skill_prompt` menambahkan `OUTPUT_SUFFIX` yang memaksa balasan
  **JSON-only** (dipakai agen trading Hermes). Dua skill ini menghasilkan **laporan prosa**,
  bukan JSON, jadi **jangan** dijalankan lewat `load_skill_prompt`. Keduanya adalah prosedur
  yang dipanggil manual oleh agent (mis. Kiro), bukan bagian dari pipeline Hermes.
- **Cara memanggil di Kiro:** minta agent menjalankan skill-nya langsung, contoh:
  - Review: "jalankan skill ponytail-review pada perubahan uncommitted" (atau sebut
    branch/PR/file).
  - Audit: "jalankan skill ponytail-audit untuk folder backend/" (atau seluruh repo).
- **Acceptance:** ✅ mekanisme discovery terverifikasi (by-convention, tak perlu edit
  registry); cara pakai terdokumentasi di sini.

### PT-4 (P3) — Catat command yang tidak didukung di Kiro ✅ DONE
- **Kategori:** J. Operational
- **Gap:** `/ponytail-debt`, `/ponytail-gain`, `/ponytail-help`, band/board, dan mode switch
  (`/ponytail lite|full|ultra|off`) butuh host skill-capable + lifecycle hooks. Kiro tidak
  menyediakannya.
- **Catatan (sesuai INSTALL.md upstream):** Di Kiro, ponytail berjalan **instruction-only** —
  hanya ruleset always-on via `.kiro/steering/ponytail.md`. Command di atas tidak tersedia.
  Untuk fitur penuh (slash-command, band/board, mode switch, `/ponytail-debt` ledger),
  jalankan project ini di **Claude Code** atau **Codex** yang mendukung plugin + hooks.
  Workflow review/audit tetap bisa dipakai di Kiro lewat skill lokal (lihat PT-3).
- **Acceptance:** ✅ catatan ada; tidak ada usaha mengimplementasikan hooks/band di Kiro.

---

## 3. Status & Batasan
- **PT-1, PT-2, PT-3, PT-4: selesai.** Yang berubah hanya file skill baru di
  `.agents/skills/` dan dokumen ini — **tidak ada kode produksi (backend/frontend/engine)
  yang diubah**.
- File baru: `.agents/skills/ponytail-review/SKILL.md`, `.agents/skills/ponytail-audit/SKILL.md`.
- Konten skill di-rephrase dari sumber upstream untuk kepatuhan lisensi (MIT).
- Prioritas (P1–P3) mengikuti konvensi backlog yang sudah ada di `docs/audit/`.

Skipped: tidak menyentuh `backend/src/agents/skills.py` — loader by-convention sudah cukup, dan dua skill ini memang tidak lewat jalur `load_skill_prompt` (lihat PT-3).
Risk: kalau nanti seseorang memanggil `load_skill_prompt("ponytail-review")`, suffix JSON-only akan merusak output laporan; dua skill ini harus dipanggil sebagai prosedur agent, bukan via loader Hermes.
