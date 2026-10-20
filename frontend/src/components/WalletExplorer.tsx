"use client";

import { motion } from "framer-motion";
import { NotConnected } from "./NotConnected";

export function WalletExplorer() {
  return (
    <motion.div
      initial={{ opacity: 0, y: 10 }}
      animate={{ opacity: 1, y: 0 }}
      className="rounded-xl border border-border bg-bg-panel p-4"
    >
      <h2 className="mb-3 text-xs font-semibold uppercase tracking-wider text-text-muted">
        Wallet Explorer &middot; Copy-Trade Candidates
      </h2>
      <NotConnected
        title="Solana Ingestion Engine belum terhubung"
        detail="Wallet discovery, skor performa, riwayat swap, dan audit keamanan token memerlukan modul Ingestion (Fase 2) yang belum diimplementasikan."
      />
    </motion.div>
  );
}
