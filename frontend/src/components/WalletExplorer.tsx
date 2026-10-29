"use client";

import { useState } from "react";
import { motion } from "framer-motion";
import { usePolling } from "@/lib/api";
import { addWallet, decideWallet, HttpError, useCurrentUser, type WalletDecision } from "@/lib/auth";
import { NotConnected } from "./NotConnected";

type WalletRow = {
  address: string;
  status: string;
  composite_score: number;
  win_rate_pct: number;
  profit_factor: number;
  net_pnl_usd: number;
  last_active_at: string | null;
};

// Operator decisions (WALLET_DISCOVERY_FLOWCHART.mmd): only a scored PENDING_REVIEW wallet can be approved.
const DECISIONS: Record<string, { status: WalletDecision; label: string }[]> = {
  DISCOVERED: [{ status: "ARCHIVED", label: "Arsipkan" }],
  PENDING_REVIEW: [
    { status: "ACTIVE_MONITORED", label: "Setujui" },
    { status: "ARCHIVED", label: "Arsipkan" },
  ],
  ACTIVE_MONITORED: [{ status: "ARCHIVED", label: "Arsipkan" }],
  APPROVED: [{ status: "ARCHIVED", label: "Arsipkan" }],
};

function failureMessage(err: unknown, onConflict: string) {
  if (err instanceof HttpError && err.status === 409) return onConflict;
  if (err instanceof HttpError && err.status === 422) return "Alamat wallet Solana tidak valid.";
  return "Gagal — backend tidak merespons atau sesi berakhir.";
}

export function WalletExplorer() {
  const isAdmin = useCurrentUser()?.role === "admin";
  // Bumping v changes the polled path, so usePolling refetches right after an action.
  const [version, setVersion] = useState(0);
  const wallets = usePolling<WalletRow[]>(`/api/v1/wallets?v=${version}`, 10000);
  const [address, setAddress] = useState("");
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<string | null>(null);

  async function act(request: () => Promise<unknown>, onConflict: string) {
    setBusy(true);
    setError(null);
    try {
      await request();
      setVersion((v) => v + 1);
      return true;
    } catch (err) {
      setError(failureMessage(err, onConflict));
      return false;
    } finally {
      setBusy(false);
    }
  }

  async function onAdd(e: React.FormEvent) {
    e.preventDefault();
    if (await act(() => addWallet(address.trim()), "Wallet ini sudah terdaftar.")) setAddress("");
  }

  return (
    <motion.div
      initial={{ opacity: 0, y: 10 }}
      animate={{ opacity: 1, y: 0 }}
      className="rounded-xl border border-border bg-bg-panel p-4"
    >
      <h2 className="mb-3 text-xs font-semibold uppercase tracking-wider text-text-muted">
        Wallet Explorer &middot; Copy-Trade Candidates
      </h2>

      {isAdmin && (
        <form onSubmit={onAdd} className="mb-3 flex gap-2">
          <input
            required
            aria-label="Alamat wallet Solana"
            placeholder="Alamat wallet Solana kandidat (base58)"
            value={address}
            onChange={(e) => setAddress(e.target.value)}
            className="w-full rounded-md border border-border bg-bg-panel-raised px-3 py-1.5 font-mono text-xs text-text outline-none focus:border-brand"
          />
          <button
            type="submit"
            disabled={busy}
            className="shrink-0 cursor-pointer rounded-md bg-brand px-3 py-1.5 text-xs font-medium text-white disabled:cursor-not-allowed disabled:opacity-50"
          >
            Tambah kandidat
          </button>
        </form>
      )}
      {error && (
        <p role="alert" className="mb-3 text-[11px] text-loss">
          {error}
        </p>
      )}

      {wallets === null ? (
        <NotConnected
          title="Backend belum terhubung"
          detail="Daftar wallet kandidat copy-trade akan muncul begitu backend merespons."
        />
      ) : wallets.length === 0 ? (
        <NotConnected
          title="Belum ada wallet ter-skor"
          detail="Admin menambahkan alamat kandidat; riwayat swap-nya dikumpulkan dan wallet dengan skor ≥ 70 dipromosikan ke PENDING_REVIEW untuk disetujui."
        />
      ) : (
        <table className="w-full text-left text-xs">
          <thead className="text-text-muted">
            <tr>
              <th className="py-1 pr-2 font-medium">Wallet</th>
              <th className="py-1 pr-2 font-medium">Status</th>
              <th className="py-1 pr-2 font-medium">Skor</th>
              <th className="py-1 pr-2 font-medium">Win%</th>
              <th className="py-1 pr-2 font-medium">PF</th>
              <th className="py-1 pr-2 font-medium">Net PnL (SOL)</th>
              {isAdmin && <th className="py-1 font-medium">Keputusan</th>}
            </tr>
          </thead>
          <tbody>
            {wallets.map((w) => (
              <tr key={w.address} className="border-t border-border">
                <td className="py-1 pr-2 font-mono" title={w.address}>{`${w.address.slice(0, 6)}…${w.address.slice(-4)}`}</td>
                <td className="py-1 pr-2">{w.status}</td>
                <td className="py-1 pr-2">{Number(w.composite_score).toFixed(2)}</td>
                <td className="py-1 pr-2">{Number(w.win_rate_pct).toFixed(1)}</td>
                <td className="py-1 pr-2">{Number(w.profit_factor).toFixed(2)}</td>
                <td className={`py-1 pr-2 ${Number(w.net_pnl_usd) >= 0 ? "text-profit" : "text-loss"}`}>
                  {Number(w.net_pnl_usd).toFixed(4)}
                </td>
                {isAdmin && (
                  <td className="space-x-2 py-1">
                    {(DECISIONS[w.status] ?? []).map((d) => (
                      <button
                        key={d.status}
                        disabled={busy}
                        onClick={() =>
                          act(
                            () => decideWallet(w.address, d.status),
                            "Status wallet sudah berubah — hanya wallet PENDING_REVIEW yang bisa disetujui.",
                          )
                        }
                        className="cursor-pointer text-brand hover:underline disabled:cursor-not-allowed disabled:opacity-50"
                      >
                        {d.label}
                      </button>
                    ))}
                  </td>
                )}
              </tr>
            ))}
          </tbody>
        </table>
      )}
    </motion.div>
  );
}
