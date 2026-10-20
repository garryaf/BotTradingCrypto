"use client";

import { AnimatePresence, motion } from "framer-motion";

/** Bull when the portfolio is up today, bear when it's down — swaps with a soft spring. */
export function ProfitLossMascot({ positive }: { positive: boolean }) {
  return (
    <AnimatePresence mode="wait">
      <motion.span
        key={positive ? "bull" : "bear"}
        initial={{ opacity: 0, scale: 0.4, rotate: positive ? -20 : 20 }}
        animate={{
          opacity: 1,
          scale: 1,
          rotate: 0,
          y: [0, -7, 0],
          filter: positive
            ? [
                "drop-shadow(0 0 4px rgba(61,220,132,0.5))",
                "drop-shadow(0 0 14px rgba(61,220,132,0.9))",
                "drop-shadow(0 0 4px rgba(61,220,132,0.5))",
              ]
            : [
                "drop-shadow(0 0 4px rgba(255,92,92,0.5))",
                "drop-shadow(0 0 14px rgba(255,92,92,0.9))",
                "drop-shadow(0 0 4px rgba(255,92,92,0.5))",
              ],
        }}
        exit={{ opacity: 0, scale: 0.4, rotate: positive ? 20 : -20 }}
        transition={{
          opacity: { duration: 0.35 },
          scale: { type: "spring", stiffness: 260, damping: 16 },
          y: { duration: 2.2, repeat: Infinity, ease: "easeInOut" },
          filter: { duration: 2.2, repeat: Infinity, ease: "easeInOut" },
        }}
        className="inline-block select-none text-3xl leading-none"
        title={positive ? "Portofolio profit hari ini" : "Portofolio rugi hari ini"}
      >
        {positive ? "🐂" : "🐻"}
      </motion.span>
    </AnimatePresence>
  );
}
