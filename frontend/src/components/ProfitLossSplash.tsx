"use client";

import { AnimatePresence, motion } from "framer-motion";
import { BullMascot } from "./mascots/BullMascot";
import { BearMascot } from "./mascots/BearMascot";

/** Full-screen bull/bear run-in, shown once per session when the portfolio first loads. */
export function ProfitLossSplash({
  show,
  positive,
  amount,
  onExitComplete,
}: {
  show: boolean;
  positive: boolean;
  amount: number;
  onExitComplete: () => void;
}) {
  const rgb = positive ? "61,220,132" : "255,92,92";
  return (
    <AnimatePresence onExitComplete={onExitComplete}>
      {show && (
        <motion.div
          initial={{ opacity: 0 }}
          animate={{ opacity: 1 }}
          exit={{ opacity: 0 }}
          transition={{ duration: 0.6 }}
          className="fixed inset-0 z-50 flex flex-col items-center justify-center overflow-hidden bg-bg/95 backdrop-blur-md"
        >
          <motion.div
            initial={{ x: "-55vw", opacity: 0, scale: 0.7 }}
            animate={{ x: 0, opacity: 1, scale: 1, y: [0, -28, 0, -16, 0] }}
            transition={{
              x: { type: "spring", stiffness: 60, damping: 14 },
              scale: { type: "spring", stiffness: 60, damping: 14 },
              opacity: { duration: 0.4 },
              y: { duration: 1.1, repeat: 2, ease: "easeInOut", delay: 0.3 },
            }}
            style={{
              filter: `drop-shadow(0 0 70px rgba(${rgb},0.85)) drop-shadow(0 0 140px rgba(${rgb},0.4))`,
            }}
            className={`select-none ${positive ? "text-profit" : "text-loss"}`}
          >
            {positive ? (
              <BullMascot className="h-[220px] w-auto sm:h-[300px]" />
            ) : (
              <BearMascot className="h-[220px] w-auto sm:h-[300px]" />
            )}
          </motion.div>

          <motion.p
            initial={{ opacity: 0, y: 24 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ delay: 0.6, duration: 0.5 }}
            className={`mt-2 font-mono text-4xl font-bold sm:text-6xl ${positive ? "text-profit" : "text-loss"}`}
          >
            {positive ? "+" : ""}${amount.toLocaleString("en-US", { minimumFractionDigits: 2, maximumFractionDigits: 2 })}
          </motion.p>

          <motion.p
            initial={{ opacity: 0 }}
            animate={{ opacity: 1 }}
            transition={{ delay: 0.9, duration: 0.5 }}
            className="mt-3 text-xs uppercase tracking-widest text-text-faint"
          >
            {positive ? "Portofolio Profit Hari Ini" : "Portofolio Rugi Hari Ini"}
          </motion.p>
        </motion.div>
      )}
    </AnimatePresence>
  );
}
