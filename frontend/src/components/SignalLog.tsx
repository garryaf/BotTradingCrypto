"use client";

import { AnimatePresence, motion } from "framer-motion";
import { NotConnected } from "./NotConnected";
import { usePolling } from "@/lib/api";

type SignalRow = {
  symbol: string;
  action: string;
  status: string;
  confidence_score: number;
  estimated_winrate_pct: number;
  rationale: string | null;
  generated_at: string;
};

const STATUS_TONE: Record<string, string> = {
  EXECUTED: "text-profit",
  PENDING: "text-warn",
  REJECTED: "text-loss",
  EXPIRED: "text-text-faint",
};

export function SignalLog() {
  const rows = usePolling<SignalRow[]>("/api/v1/signals", 5000);

  if (!rows) {
    return (
      <div className="rounded-xl border border-border bg-bg-panel p-4">
        <h2 className="mb-3 text-xs font-semibold uppercase tracking-wider text-text-muted">Log Audit Sinyal AI</h2>
        <NotConnected
          compact
          title="Belum ada sinyal tercatat"
          detail="Hermes Orchestrator & Deterministic Risk Engine belum berjalan — log PASSED/REJECTED/EXPIRED akan tampil di sini."
        />
      </div>
    );
  }

  if (rows.length === 0) {
    return (
      <div className="rounded-xl border border-border bg-bg-panel p-4">
        <h2 className="mb-3 text-xs font-semibold uppercase tracking-wider text-text-muted">Log Audit Sinyal AI</h2>
        <p className="py-6 text-center text-xs text-text-faint">Belum ada sinyal.</p>
      </div>
    );
  }

  return (
    <div className="rounded-xl border border-border bg-bg-panel p-4">
      <h2 className="mb-3 text-xs font-semibold uppercase tracking-wider text-text-muted">Log Audit Sinyal AI</h2>
      <div className="space-y-1.5">
        <AnimatePresence initial={false}>
          {rows.map((s, i) => (
            <motion.div
              key={s.generated_at}
              layout
              initial={{ opacity: 0, y: -10, backgroundColor: "rgba(255,255,255,0.08)" }}
              animate={{
                opacity: 1,
                y: 0,
                backgroundColor: "rgba(255,255,255,0)",
                transition: { duration: 0.4, delay: Math.min(i, 8) * 0.04 },
              }}
              exit={{
                opacity: 0,
                height: 0,
                marginBottom: 0,
                paddingTop: 0,
                paddingBottom: 0,
                transition: { duration: 0.22 },
              }}
              className="overflow-hidden rounded-md border border-border-soft px-3 py-2 text-xs"
            >
              <div className="flex items-center justify-between">
                <span className="font-medium text-text">
                  {s.symbol} · {s.action}
                </span>
                <span className={`text-[10px] font-semibold ${STATUS_TONE[s.status] ?? "text-text-faint"}`}>
                  {s.status}
                </span>
              </div>
              <p className="mt-0.5 text-[11px] text-text-faint">
                conf {(s.confidence_score * 100).toFixed(0)}% · winrate {s.estimated_winrate_pct.toFixed(0)}%
              </p>
              {s.rationale && <p className="mt-1 text-[11px] text-text-muted">{s.rationale}</p>}
            </motion.div>
          ))}
        </AnimatePresence>
      </div>
    </div>
  );
}
