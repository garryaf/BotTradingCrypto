"use client";

import { motion } from "framer-motion";
import { NotConnected } from "./NotConnected";
import { usePolling } from "@/lib/api";

type PortfolioResponse = {
  connected: boolean;
  equity_usd: number;
  cash_balance_usd: number;
  open_positions_value_usd: number;
  daily_loss_pct: number;
  current_drawdown_pct: number;
  high_water_mark_usd: number;
  history: { time: string; equity: number }[];
};

function Sparkline({ points }: { points: number[] }) {
  if (points.length < 2) return null;
  const min = Math.min(...points);
  const max = Math.max(...points);
  const range = max - min || 1;
  const w = 100;
  const h = 28;
  const path = points
    .map((v, i) => `${(i / (points.length - 1)) * w},${h - ((v - min) / range) * h}`)
    .join(" ");
  const up = points[points.length - 1] >= points[0];
  return (
    <svg viewBox={`0 0 ${w} ${h}`} className="h-7 w-24" preserveAspectRatio="none">
      <polyline
        points={path}
        fill="none"
        strokeWidth={1.5}
        vectorEffect="non-scaling-stroke"
        className={up ? "stroke-profit" : "stroke-loss"}
      />
    </svg>
  );
}

function Stat({ label, value, tone }: { label: string; value: string; tone?: "profit" | "loss" }) {
  return (
    <div>
      <p className="text-[10px] uppercase tracking-wide text-text-faint">{label}</p>
      <p className={`font-mono text-sm ${tone === "profit" ? "text-profit" : tone === "loss" ? "text-loss" : "text-text"}`}>
        {value}
      </p>
    </div>
  );
}

export function EquityHero() {
  const data = usePolling<PortfolioResponse>("/api/v1/portfolio", 5000);

  if (!data || !data.connected) {
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

  const dailyProfit = data.daily_loss_pct <= 0;
  const equityPoints = data.history.map((h) => h.equity);

  return (
    <motion.div initial={{ opacity: 0 }} animate={{ opacity: 1 }} className="rounded-xl border border-border bg-bg-panel p-5">
      <div className="flex items-start justify-between">
        <div>
          <h2 className="mb-1 text-[11px] font-semibold uppercase tracking-wide text-text-faint">
            Equity Portofolio (Paper)
          </h2>
          <p className="font-mono text-2xl font-semibold text-text">
            ${data.equity_usd.toLocaleString("en-US", { minimumFractionDigits: 2, maximumFractionDigits: 2 })}
          </p>
        </div>
        <Sparkline points={equityPoints} />
      </div>
      <div className="mt-4 grid grid-cols-2 gap-3 sm:grid-cols-4">
        <Stat label="Kas" value={`$${data.cash_balance_usd.toFixed(2)}`} />
        <Stat label="Posisi" value={`$${data.open_positions_value_usd.toFixed(2)}`} />
        <Stat
          label="Daily Loss"
          value={`${data.daily_loss_pct.toFixed(2)}%`}
          tone={dailyProfit ? "profit" : "loss"}
        />
        <Stat
          label="Drawdown"
          value={`${data.current_drawdown_pct.toFixed(2)}%`}
          tone={data.current_drawdown_pct > 0 ? "loss" : "profit"}
        />
      </div>
    </motion.div>
  );
}
