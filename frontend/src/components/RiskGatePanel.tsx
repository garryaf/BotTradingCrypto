"use client";

import { NotConnected } from "./NotConnected";

export function RiskGatePanel() {
  return (
    <div className="rounded-xl border border-border bg-bg-panel p-4">
      <h2 className="mb-3 text-xs font-semibold uppercase tracking-wider text-text-muted">
        Risk Gate — 9 Pintu
      </h2>
      <NotConnected
        title="Risk Engine belum terhubung"
        detail="Status 9 pintu deterministik (OPEN_QUESTIONS.md Q-08) hanya dapat ditampilkan setelah Deterministic Risk Engine berjalan di backend."
      />
    </div>
  );
}
