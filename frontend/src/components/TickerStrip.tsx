"use client";

import { useEffect, useRef, useState } from "react";
import { motion } from "framer-motion";
import { subscribeTicker, type TickerData } from "@/lib/binance";

const SYMBOLS = ["BTCUSDT", "ETHUSDT", "SOLUSDT"];

function Tick({ symbol, active, onClick }: { symbol: string; active: boolean; onClick: () => void }) {
  const [data, setData] = useState<TickerData | null>(null);
  const [dir, setDir] = useState<"up" | "down" | null>(null);
  const lastPrice = useRef<number | null>(null);

  useEffect(() => {
    return subscribeTicker(symbol, (d) => {
      if (lastPrice.current !== null) {
        setDir(d.lastPrice >= lastPrice.current ? "up" : "down");
      }
      lastPrice.current = d.lastPrice;
      setData(d);
    });
  }, [symbol]);

  const positive = (data?.pct24h ?? 0) >= 0;

  return (
    <button
      onClick={onClick}
      className={`flex items-center gap-3 rounded-lg border px-3.5 py-2.5 text-left transition-colors ${
        active
          ? "border-border bg-bg-panel-raised"
          : "border-transparent hover:border-border-soft hover:bg-bg-panel-raised/50"
      }`}
    >
      <span className="text-xs font-medium tracking-wide text-text-muted">
        {symbol.replace("USDT", "")}
        <span className="text-text-faint">/USDT</span>
      </span>
      {data ? (
        <motion.span
          key={data.lastPrice}
          initial={{
            backgroundColor:
              dir === "up"
                ? "rgba(0,230,118,0.35)"
                : dir === "down"
                ? "rgba(255,59,48,0.35)"
                : "rgba(0,0,0,0)",
          }}
          animate={{ backgroundColor: "rgba(0,0,0,0)" }}
          transition={{ duration: 0.9 }}
          className="rounded px-1 font-mono text-sm tabular-nums text-text"
        >
          {data.lastPrice.toLocaleString("en-US", { maximumFractionDigits: 4 })}
        </motion.span>
      ) : (
        <span className="h-4 w-16 animate-pulse rounded bg-white/5" />
      )}
      {data && (
        <span className={`font-mono text-xs tabular-nums ${positive ? "text-profit" : "text-loss"}`}>
          {positive ? "+" : ""}
          {data.pct24h.toFixed(2)}%
        </span>
      )}
    </button>
  );
}

export function TickerStrip({ active, onSelect }: { active: string; onSelect: (s: string) => void }) {
  return (
    <div className="flex items-center gap-1.5 overflow-x-auto">
      {SYMBOLS.map((s) => (
        <Tick key={s} symbol={s} active={active === s} onClick={() => onSelect(s)} />
      ))}
    </div>
  );
}
