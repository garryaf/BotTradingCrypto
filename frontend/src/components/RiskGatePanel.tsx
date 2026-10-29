"use client";

import { motion } from "framer-motion";
import { Check, X } from "lucide-react";
import { NotConnected } from "./NotConnected";
import { usePolling } from "@/lib/api";

// Thresholds the backend gates enforce (risk/engine.py risk_limits) — labels read these, never a copy.
type Limits = {
  max_risk_per_trade_pct: number;
  daily_loss_limit_pct: number;
  max_drawdown_limit_pct: number;
  max_spread_pct: number;
  min_24h_volume_usd: number;
  max_open_positions: number;
  data_freshness_max_age_sec: number;
};

type RiskStatus = {
  paused: boolean;
  circuit_breaker_active: boolean;
  daily_loss_pct: number;
  current_drawdown_pct: number;
  limits: Limits;
  latest_check: {
    passed: boolean;
    rejection_reasons: string[];
    expectancy_check: boolean;
    risk_per_trade_check: boolean;
    daily_loss_check: boolean;
    drawdown_check: boolean;
    spread_check: boolean;
    stop_loss_check: boolean;
    balance_lot_check: boolean;
    max_positions_check: boolean;
    circuit_breaker_check: boolean;
    data_freshness_check: boolean;
    evaluated_at: string;
  } | null;
};

// toFixed strips float noise (0.0035 * 100 = 0.35000000000000003).
const pct = (fraction: number) => +(fraction * 100).toFixed(4);

function gates(l: Limits): { key: keyof NonNullable<RiskStatus["latest_check"]>; label: string }[] {
  return [
    { key: "expectancy_check", label: "1. Expectancy Positif (net fee)" },
    { key: "risk_per_trade_check", label: `2. Risk per Trade ≤ ${pct(l.max_risk_per_trade_pct)}%` },
    { key: "daily_loss_check", label: `3. Daily Loss < ${l.daily_loss_limit_pct}%` },
    { key: "drawdown_check", label: `4. Drawdown < ${l.max_drawdown_limit_pct}%` },
    {
      key: "spread_check",
      label: `5. Spread ≤ ${l.max_spread_pct}% & Vol 24h ≥ $${(l.min_24h_volume_usd / 1_000_000).toLocaleString("en-US")}M`,
    },
    { key: "stop_loss_check", label: "6. Stop Loss Valid" },
    { key: "balance_lot_check", label: "7. Saldo & Lot Size" },
    { key: "max_positions_check", label: `8. Posisi Terbuka < ${l.max_open_positions}` },
    { key: "circuit_breaker_check", label: "8b. Circuit Breaker" },
    { key: "data_freshness_check", label: `9. Data ≤ ${l.data_freshness_max_age_sec} detik` },
  ];
}

export function RiskGatePanel() {
  const data = usePolling<RiskStatus>("/api/v1/risk/status", 5000);

  if (!data || !data.latest_check) {
    return (
      <div className="rounded-xl border border-border bg-bg-panel p-4">
        <h2 className="mb-3 text-xs font-semibold uppercase tracking-wider text-text-muted">Risk Gate — 9 Pintu</h2>
        <NotConnected
          title="Risk Engine belum terhubung"
          detail="Status 9 pintu deterministik (OPEN_QUESTIONS.md Q-08) hanya dapat ditampilkan setelah Deterministic Risk Engine berjalan di backend."
        />
      </div>
    );
  }

  const check = data.latest_check;

  return (
    <div className="rounded-xl border border-border bg-bg-panel p-4">
      <div className="mb-3 flex items-center justify-between">
        <h2 className="text-xs font-semibold uppercase tracking-wider text-text-muted">Risk Gate — 9 Pintu</h2>
        {data.circuit_breaker_active && (
          <span className="rounded-full bg-loss/10 px-2 py-0.5 text-[10px] font-semibold text-loss">
            CIRCUIT BREAKER AKTIF
          </span>
        )}
      </div>
      <div className="grid grid-cols-1 gap-1.5 sm:grid-cols-2">
        {gates(data.limits).map((gate) => {
          const passed = check[gate.key] as boolean;
          return (
            <motion.div
              key={gate.key}
              animate={!passed ? { x: [0, -3, 3, -3, 3, 0] } : {}}
              transition={{ duration: 0.4 }}
              className={`flex items-center gap-2 rounded-md border px-2.5 py-1.5 ${
                passed ? "border-border-soft" : "border-loss/40 bg-loss/5"
              }`}
            >
              {passed ? <Check size={13} className="text-profit" /> : <X size={13} className="text-loss" />}
              <span className="text-[11px] text-text-muted">{gate.label}</span>
            </motion.div>
          );
        })}
      </div>
      {!check.passed && check.rejection_reasons.length > 0 && (
        <p className="mt-3 text-[11px] text-loss">Ditolak: {check.rejection_reasons.join(", ")}</p>
      )}
    </div>
  );
}
