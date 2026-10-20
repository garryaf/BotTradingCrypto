"use client";

import { useState } from "react";
import { motion } from "framer-motion";
import { CandleChart, INTERVALS } from "@/components/CandleChart";
import { TickerStrip } from "@/components/TickerStrip";
import { EquityHero } from "@/components/EquityHero";
import { PositionsTable } from "@/components/PositionsTable";
import { SignalLog } from "@/components/SignalLog";

export default function Home() {
  const [symbol, setSymbol] = useState("BTCUSDT");
  const [timeframe, setTimeframe] = useState("15m");

  return (
    <>
      <motion.div initial={{ opacity: 0, y: 10 }} animate={{ opacity: 1, y: 0 }} transition={{ delay: 0.05 }}>
        <EquityHero />
      </motion.div>

      <motion.div
        initial={{ opacity: 0, y: 10 }}
        animate={{ opacity: 1, y: 0 }}
        transition={{ delay: 0.1 }}
        className="mt-4 flex flex-col gap-3 rounded-xl border border-border bg-bg-panel p-4"
      >
        <div className="flex flex-wrap items-center justify-between gap-3">
          <TickerStrip active={symbol} onSelect={setSymbol} />
          <div className="flex gap-1 rounded-lg border border-border-soft p-0.5">
            {INTERVALS.map((it) => (
              <button
                key={it.value}
                onClick={() => setTimeframe(it.value)}
                className={`rounded-md px-2.5 py-1 text-xs font-medium transition-colors ${
                  timeframe === it.value
                    ? "bg-bg-panel-raised text-text"
                    : "text-text-faint hover:text-text-muted"
                }`}
              >
                {it.label}
              </button>
            ))}
          </div>
        </div>
        <div className="h-[380px]">
          <CandleChart symbol={symbol} interval={timeframe} />
        </div>
      </motion.div>

      <div className="mt-4 grid grid-cols-1 gap-4 lg:grid-cols-2">
        <motion.div initial={{ opacity: 0, y: 10 }} animate={{ opacity: 1, y: 0 }} transition={{ delay: 0.15 }}>
          <PositionsTable />
        </motion.div>
        <motion.div initial={{ opacity: 0, y: 10 }} animate={{ opacity: 1, y: 0 }} transition={{ delay: 0.2 }}>
          <SignalLog />
        </motion.div>
      </div>

      <footer className="mt-6 flex justify-between text-[11px] text-text-faint">
        <span>Sumber data: Binance Public Data API &middot; Tanpa kunci privat blockchain</span>
        <span>
          Live Trading: <span className="font-mono text-loss">LOCKED (Fase 0–6)</span>
        </span>
      </footer>
    </>
  );
}
