"use client";

import { AnimatePresence, motion } from "framer-motion";
import { NotConnected } from "./NotConnected";
import { usePolling } from "@/lib/api";
import { PnlGlow } from "./PnlGlow";
import { CountUp } from "./CountUp";

type PositionRow = {
  id: string;
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
        <AnimatePresence initial={false}>
          {rows.map((p) => {
            const pnl = (p.unrealized_pnl_usd ?? 0) + p.realized_pnl_usd;
            const positive = pnl >= 0;
            return (
              <motion.div
                key={p.id}
                layout
                initial={{ opacity: 0, x: -12 }}
                animate={{ opacity: 1, x: 0 }}
                exit={{ opacity: 0, x: 12, height: 0, marginBottom: 0, paddingTop: 0, paddingBottom: 0 }}
                transition={{ duration: 0.3 }}
                className="flex items-center justify-between overflow-hidden rounded-md border border-border-soft px-3 py-2 text-xs"
              >
                <div className="flex items-center gap-2">
                  <span className="font-medium text-text">{p.symbol}</span>
                  <span className="text-[10px] text-text-faint">{p.status}</span>
                  {p.is_tp1_hit && <span className="text-[10px] text-profit">TP1 ✓</span>}
                </div>
                <span className="font-mono text-text-muted">
                  {p.quantity.toFixed(6)} @ {p.average_entry_price.toFixed(2)}
                </span>
                <PnlGlow positive={positive} intensity="sm">
                  <span className={`font-mono ${positive ? "text-profit" : "text-loss"}`}>
                    {positive ? "+" : ""}
                    <CountUp value={pnl} format={(n) => n.toFixed(2)} />
                  </span>
                </PnlGlow>
              </motion.div>
            );
          })}
        </AnimatePresence>
      </div>
    </div>
  );
}
