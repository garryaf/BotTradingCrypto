"use client";

import { NotConnected } from "./NotConnected";

export function PositionsTable() {
  return (
    <div className="rounded-xl border border-border bg-bg-panel p-4">
      <h2 className="mb-3 text-xs font-semibold uppercase tracking-wider text-text-muted">
        Posisi Terbuka
      </h2>
      <NotConnected
        compact
        title="Belum ada data posisi"
        detail="Paper Broker Simulator belum berjalan — posisi aktif akan muncul di sini setelah backend tersambung."
      />
    </div>
  );
}
