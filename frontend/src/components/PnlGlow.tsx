"use client";

import { motion } from "framer-motion";
import { ReactNode } from "react";

const PROFIT_RGB = "0,230,118"; // --profit
const LOSS_RGB = "255,59,48"; // --loss

function glowLayers(rgb: string, scale: number, alpha: number) {
  return [
    `0 0 ${6 * scale}px rgba(${rgb},${alpha})`,
    `0 0 ${16 * scale}px rgba(${rgb},${alpha * 0.65})`,
    `0 0 ${32 * scale}px rgba(${rgb},${alpha * 0.4})`,
  ].join(", ");
}

/** Elegant neon text-glow that breathes — green when in profit, red when in loss. */
export function PnlGlow({
  positive,
  intensity = "lg",
  children,
}: {
  positive: boolean;
  intensity?: "lg" | "sm";
  children: ReactNode;
}) {
  const rgb = positive ? PROFIT_RGB : LOSS_RGB;
  const scale = intensity === "lg" ? 1 : 0.55;
  return (
    <motion.span
      style={{ display: "inline-block" }}
      animate={{ textShadow: [glowLayers(rgb, scale, 0.55), glowLayers(rgb, scale, 1), glowLayers(rgb, scale, 0.55)] }}
      transition={{ duration: 2.2, repeat: Infinity, ease: "easeInOut" }}
    >
      {children}
    </motion.span>
  );
}
