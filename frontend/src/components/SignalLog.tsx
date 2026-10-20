"use client";

import { NotConnected } from "./NotConnected";

export function SignalLog() {
  return (
    <div className="rounded-xl border border-border bg-bg-panel p-4">
      <h2 className="mb-3 text-xs font-semibold uppercase tracking-wider text-text-muted">
        Log Audit Sinyal AI
      </h2>
      <NotConnected
        compact
        title="Belum ada sinyal tercatat"
        detail="Hermes Orchestrator & Deterministic Risk Engine belum berjalan — log PASSED/REJECTED/EXPIRED akan tampil di sini."
      />
    </div>
  );
}
