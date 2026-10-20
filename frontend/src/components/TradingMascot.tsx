"use client";

import { useEffect, useRef, useState } from "react";
import { AnimatePresence, motion } from "framer-motion";
import { subscribeTicker, type TickerData } from "@/lib/binance";

const BULLISH_LINES = ["To the moon! 🚀", "Pamp it!", "Diamond hands 💎", "Yuk gaskeun!"];
const BEARISH_LINES = ["Buy the dip?", "Sabar ya...", "HODL dulu 🙏", "Cuan nanti balik"];

export function TradingMascot() {
  const [data, setData] = useState<TickerData | null>(null);
  const [pulse, setPulse] = useState(0);
  const lastPrice = useRef<number | null>(null);

  useEffect(() => {
    return subscribeTicker("BTCUSDT", (d) => {
      if (lastPrice.current !== null && d.lastPrice !== lastPrice.current) {
        setPulse((p) => p + 1);
      }
      lastPrice.current = d.lastPrice;
      setData(d);
    });
  }, []);

  const bullish = (data?.pct24h ?? 0) >= 0;
  const lines = bullish ? BULLISH_LINES : BEARISH_LINES;
  const line = lines[pulse % lines.length];

  return (
    <div className="relative flex items-center" title="Mood pasar BTC/USDT 24h">
      <motion.div
        animate={{ y: [0, -5, 0], rotate: bullish ? [0, -8, 0] : [0, 8, 0] }}
        transition={{ duration: 1.8, repeat: Infinity, ease: "easeInOut" }}
        className="text-lg leading-none select-none"
      >
        {!data ? "💤" : bullish ? "🚀" : "🐻"}
      </motion.div>

      <AnimatePresence mode="wait">
        {data && (
          <motion.span
            key={line}
            initial={{ opacity: 0, x: -4 }}
            animate={{ opacity: 1, x: 0 }}
            exit={{ opacity: 0 }}
            transition={{ duration: 0.3 }}
            className={`ml-1.5 whitespace-nowrap text-[11px] font-medium ${
              bullish ? "text-profit" : "text-loss"
            }`}
          >
            {line}
          </motion.span>
        )}
      </AnimatePresence>
    </div>
  );
}
