"use client";

import Link from "next/link";
import { usePathname } from "next/navigation";
import { motion } from "framer-motion";
import { Activity, Boxes } from "lucide-react";
import { KillSwitch } from "./KillSwitch";

const NAV = [
  { href: "/", label: "Dashboard" },
  { href: "/risk", label: "Risk Monitor" },
  { href: "/wallets", label: "Wallet Explorer" },
];

export function AppHeader() {
  const pathname = usePathname();

  return (
    <motion.header
      initial={{ opacity: 0, y: -8 }}
      animate={{ opacity: 1, y: 0 }}
      className="mb-5 flex flex-wrap items-center justify-between gap-3"
    >
      <div className="flex items-center gap-6">
        <div className="flex items-center gap-3">
          <Boxes size={18} className="text-brand" />
          <div>
            <h1 className="text-sm font-semibold tracking-wide text-text">AUTO-TRADE AA</h1>
            <p className="text-[11px] text-text-faint">Hermes Multi-Agent Orchestrator</p>
          </div>
        </div>

        <nav className="flex items-center gap-1 rounded-lg border border-border-soft p-0.5">
          {NAV.map((item) => (
            <Link
              key={item.href}
              href={item.href}
              className={`rounded-md px-3 py-1.5 text-xs font-medium transition-colors ${
                pathname === item.href
                  ? "bg-bg-panel-raised text-text"
                  : "text-text-faint hover:text-text-muted"
              }`}
            >
              {item.label}
            </Link>
          ))}
        </nav>
      </div>

      <div className="flex items-center gap-3">
        <span className="flex items-center gap-1.5 rounded-full border border-warn/30 bg-warn/10 px-2.5 py-1 text-[11px] font-medium text-warn">
          <span className="animate-blink-dot h-1.5 w-1.5 rounded-full bg-warn" />
          PAPER TRADING
        </span>
        <span className="flex items-center gap-1.5 text-[11px] text-text-faint">
          <Activity size={12} className="text-profit" />
          Live &middot; Binance Spot
        </span>
        <KillSwitch />
      </div>
    </motion.header>
  );
}
