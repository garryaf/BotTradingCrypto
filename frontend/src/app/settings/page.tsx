"use client";

import { useEffect, useState } from "react";
import { motion, AnimatePresence } from "framer-motion";
import { CheckCircle2, Eye, EyeOff } from "lucide-react";
import { getBinanceCredentials, saveBinanceCredentials } from "@/lib/auth";

export default function SettingsPage() {
  const [apiKey, setApiKey] = useState("");
  const [apiSecret, setApiSecret] = useState("");
  const [showSecret, setShowSecret] = useState(false);
  const [last4, setLast4] = useState<string | null>(null);
  const [status, setStatus] = useState<"idle" | "saving" | "saved" | "error">("idle");
  const [loadFailed, setLoadFailed] = useState(false);

  useEffect(() => {
    getBinanceCredentials()
      .then((c) => setLast4(c.api_key_last4))
      // Without this the page silently reads as "no key saved" when the backend is just unreachable.
      .catch(() => setLoadFailed(true));
  }, []);

  async function onSubmit(e: React.FormEvent) {
    e.preventDefault();
    setStatus("saving");
    try {
      const result = await saveBinanceCredentials(apiKey, apiSecret);
      setLast4(result.api_key_last4);
      setApiKey("");
      setApiSecret("");
      setStatus("saved");
    } catch {
      setStatus("error");
    }
  }

  return (
    <div className="mx-auto max-w-lg">
      <h1 className="mb-1 text-sm font-semibold text-text">Binance API Key</h1>
      <p className="mb-5 text-[11px] text-text-faint">
        1 akun Binance per 1 user. Key disimpan terenkripsi — hanya 4 digit terakhir yang pernah ditampilkan lagi.
      </p>

      {loadFailed && (
        <p role="alert" className="mb-4 rounded-md border border-loss/40 px-3 py-2 text-[12px] text-loss">
          Status key tidak bisa dimuat — backend tidak merespons. Key yang tersimpan (jika ada) tidak terlihat di sini.
        </p>
      )}

      <AnimatePresence>
        {last4 && (
          <motion.p
            initial={{ opacity: 0, y: -6 }}
            animate={{ opacity: 1, y: 0 }}
            exit={{ opacity: 0, height: 0, marginBottom: 0 }}
            className="mb-4 rounded-md border border-border bg-bg-panel-raised px-3 py-2 text-[12px] text-text-muted"
          >
            Key aktif berakhiran <span className="font-mono text-text">****{last4}</span>
          </motion.p>
        )}
      </AnimatePresence>

      <motion.form
        initial={{ opacity: 0, y: 10 }}
        animate={{ opacity: 1, y: 0 }}
        transition={{ duration: 0.25 }}
        onSubmit={onSubmit}
        className="rounded-xl border border-border bg-bg-panel p-6"
      >
        <label className="mb-1 block text-[11px] text-text-muted">API Key</label>
        <input
          required
          autoComplete="off"
          value={apiKey}
          onChange={(e) => setApiKey(e.target.value)}
          className="mb-3 w-full rounded-md border border-border bg-bg-panel-raised px-3 py-2 text-sm text-text outline-none transition-colors focus:border-brand"
        />

        <label className="mb-1 block text-[11px] text-text-muted">API Secret</label>
        <div className="relative mb-4">
          <input
            type={showSecret ? "text" : "password"}
            required
            autoComplete="off"
            value={apiSecret}
            onChange={(e) => setApiSecret(e.target.value)}
            className="w-full rounded-md border border-border bg-bg-panel-raised px-3 py-2 pr-9 text-sm text-text outline-none transition-colors focus:border-brand"
          />
          <button
            type="button"
            onClick={() => setShowSecret((v) => !v)}
            aria-label={showSecret ? "Sembunyikan secret" : "Tampilkan secret"}
            className="absolute right-2.5 top-1/2 -translate-y-1/2 cursor-pointer text-text-faint hover:text-text-muted"
          >
            {showSecret ? <EyeOff size={14} /> : <Eye size={14} />}
          </button>
        </div>

        <AnimatePresence mode="wait">
          {status === "error" && (
            <motion.p
              key="error"
              initial={{ opacity: 0 }}
              animate={{ opacity: 1 }}
              exit={{ opacity: 0 }}
              className="mb-3 text-[11px] text-loss"
            >
              Gagal menyimpan, coba lagi.
            </motion.p>
          )}
          {status === "saved" && (
            <motion.p
              key="saved"
              initial={{ opacity: 0, scale: 0.95 }}
              animate={{ opacity: 1, scale: 1 }}
              exit={{ opacity: 0 }}
              className="mb-3 flex items-center gap-1.5 text-[11px] text-profit"
            >
              <CheckCircle2 size={13} /> Tersimpan.
            </motion.p>
          )}
        </AnimatePresence>

        <button
          type="submit"
          disabled={status === "saving"}
          className="w-full cursor-pointer rounded-md bg-brand px-3 py-2 text-sm font-medium text-white transition-opacity hover:opacity-90 disabled:cursor-not-allowed disabled:opacity-50"
        >
          {status === "saving" ? "Menyimpan..." : "Simpan"}
        </button>
      </motion.form>
    </div>
  );
}
