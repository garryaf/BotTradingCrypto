"use client";

import { NotConnected } from "./NotConnected";

export function EquityHero() {
  return (
    <div className="rounded-xl border border-border bg-bg-panel p-5">
      <h2 className="mb-3 text-[11px] font-semibold uppercase tracking-wide text-text-faint">
        Equity Portofolio (Paper)
      </h2>
      <NotConnected
        title="Portfolio backend belum terhubung"
        detail="Equity, PnL, win rate, dan limit risiko memerlukan FastAPI + PostgreSQL + Risk Engine (Fase 1-4), yang belum diimplementasikan."
      />
    </div>
  );
}
