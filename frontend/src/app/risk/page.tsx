"use client";

import { motion } from "framer-motion";
import { ShieldAlert } from "lucide-react";
import { RiskGatePanel } from "@/components/RiskGatePanel";

export default function RiskMonitorPage() {
  return (
    <>
      <motion.div
        initial={{ opacity: 0, y: 10 }}
        animate={{ opacity: 1, y: 0 }}
        className="mb-4 flex items-center gap-2 text-sm text-text-muted"
      >
        <ShieldAlert size={16} className="text-brand" />
        Risk Monitor &mdash; batas keselamatan portofolio ditegakkan secara deterministik, fail-closed.
      </motion.div>

      <motion.div initial={{ opacity: 0, y: 10 }} animate={{ opacity: 1, y: 0 }} transition={{ delay: 0.05 }}>
        <RiskGatePanel />
      </motion.div>
    </>
  );
}
