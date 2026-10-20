"use client";

import { NotConnected } from "./NotConnected";
import { usePolling } from "@/lib/api";

type PositionRow = {
  symbol: string;
  status: string;
  quantity: number;
  average_entry_price: number;
  current_stop_loss: number;
  take_profit_1: number;
  take_profit_2: number;
  is_tp1_hit: boolean;
  realized_pnl_usd: number;
  unrealized_pnl_usd: number | null;
};

export function PositionsTable() {
  const rows = usePolling<PositionRow[]>("/api/v1/positions", 5000);

  if (!rows) {
    return (
      <div className="rounded-xl border border-border bg-bg-panel p-4">
        <h2 className="mb-3 text-xs font-semibold uppercase tracking-wider text-text-muted">Posisi Terbuka</h2>
        <NotConnected
          compact
          title="Belum ada data posisi"
          detail="Paper Broker Simulator belum berjalan — posisi aktif akan muncul di sini setelah backend tersambung."
        />
      </div>
    );
  }

  if (rows.length === 0) {
    return (
      <div className="rounded-xl border border-border bg-bg-panel p-4">
        <h2 className="mb-3 text-xs font-semibold uppercase tracking-wider text-text-muted">Posisi Terbuka</h2>
        <p className="py-6 text-center text-xs text-text-faint">Belum ada posisi.</p>
      </div>
    );
  }

  return (
    <div className="rounded-xl border border-border bg-bg-panel p-4">
      <h2 className="mb-3 text-xs font-semibold uppercase tracking-wider text-text-muted">Posisi Terbuka</h2>
      <div className="space-y-1.5">
        {rows.map((p, i) => {
          const pnl = (p.unrealized_pnl_usd ?? 0) + p.realized_pnl_usd;
          return (
            <div key={i} className="flex items-center justify-between rounded-md border border-border-soft px-3 py-2 text-xs">
              <div className="flex items-center gap-2">
                <span className="font-medium text-text">{p.symbol}</span>
                <span className="text-[10px] text-text-faint">{p.status}</span>
                {p.is_tp1_hit && <span className="text-[10px] text-profit">TP1 ✓</span>}
              </div>
              <span className="font-mono text-text-muted">
                {p.quantity.toFixed(6)} @ {p.average_entry_price.toFixed(2)}
              </span>
              <span className={`font-mono ${pnl >= 0 ? "text-profit" : "text-loss"}`}>
                {pnl >= 0 ? "+" : ""}
                {pnl.toFixed(2)}
              </span>
            </div>
          );
        })}
      </div>
    </div>
  );
}
