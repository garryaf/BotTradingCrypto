"use client";

import { useRef, useState } from "react";
import { AnimatePresence, motion } from "framer-motion";
import { Power, ShieldCheck } from "lucide-react";
import { apiPost } from "@/lib/api";

const HOLD_MS = 1200;

export function KillSwitch() {
  const [open, setOpen] = useState(false);
  const [progress, setProgress] = useState(0);
  const [engaged, setEngaged] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const frame = useRef<number | null>(null);
  const start = useRef(0);

  // An emergency stop must never report "engaged" unless the backend confirmed it.
  const alert = error && (
    <p
      role="alert"
      className="absolute right-0 top-full z-20 mt-2 w-64 rounded-lg border border-loss/40 bg-bg-panel-raised p-2.5 text-[11px] text-loss"
    >
      {error}
    </p>
  );

  function stopHold() {
    if (frame.current) cancelAnimationFrame(frame.current);
    frame.current = null;
    setProgress(0);
  }

  function startHold() {
    start.current = performance.now();
    const tick = () => {
      const pct = Math.min((performance.now() - start.current) / HOLD_MS, 1);
      setProgress(pct);
      if (pct >= 1) {
        setOpen(false);
        stopHold();
        apiPost("/api/v1/control/kill")
          .then(() => {
            setError(null);
            setEngaged(true);
          })
          .catch(() => setError("EMERGENCY STOP GAGAL dikirim — sistem BELUM dihentikan. Cek koneksi/sesi lalu coba lagi."));
        return;
      }
      frame.current = requestAnimationFrame(tick);
    };
    frame.current = requestAnimationFrame(tick);
  }

  if (engaged) {
    return (
      <div className="relative">
        <motion.button
          initial={{ scale: 0.9, opacity: 0 }}
          animate={{ scale: 1, opacity: 1 }}
          onClick={() =>
            apiPost("/api/v1/control/resume")
              .then(() => {
                setError(null);
                setEngaged(false);
              })
              .catch(() => setError("Resume gagal — sistem masih dihentikan."))
          }
          className="flex items-center gap-2 rounded-lg border border-profit/30 bg-profit/10 px-3.5 py-2 text-xs font-medium text-profit"
        >
          <ShieldCheck size={14} />
          LIVE LOCK ENGAGED
        </motion.button>
        {alert}
      </div>
    );
  }

  return (
    <div className="relative">
      <motion.button
        whileTap={{ scale: 0.96 }}
        onClick={() => setOpen((v) => !v)}
        className="animate-pulse-ring flex items-center gap-2 rounded-lg border border-loss/40 bg-loss/10 px-3.5 py-2 text-xs font-semibold tracking-wide text-loss"
      >
        <Power size={14} />
        EMERGENCY STOP
      </motion.button>

      <AnimatePresence>
        {open && (
          <motion.div
            initial={{ opacity: 0, y: -6, scale: 0.98 }}
            animate={{ opacity: 1, y: 0, scale: 1 }}
            exit={{ opacity: 0, y: -6, scale: 0.98 }}
            transition={{ duration: 0.15 }}
            className="absolute right-0 top-full z-20 mt-2 w-64 rounded-xl border border-border bg-bg-panel-raised p-4 shadow-2xl shadow-black/50"
          >
            <p className="text-xs leading-relaxed text-text-muted">
              Hentikan seluruh entry baru &amp; bekukan agent dalam &le;2 detik. Tahan tombol untuk konfirmasi.
            </p>
            <button
              onPointerDown={startHold}
              onPointerUp={stopHold}
              onPointerLeave={stopHold}
              className="relative mt-3 w-full overflow-hidden rounded-lg border border-loss/40 bg-loss/5 py-2.5 text-xs font-semibold text-loss select-none"
            >
              <motion.div
                className="absolute inset-y-0 left-0 bg-loss/30"
                style={{ width: `${progress * 100}%` }}
              />
              <span className="relative">TAHAN UNTUK KONFIRMASI</span>
            </button>
          </motion.div>
        )}
      </AnimatePresence>
      {!open && alert}
    </div>
  );
}
