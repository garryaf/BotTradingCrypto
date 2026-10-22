"use client";

import { useEffect, useState } from "react";
import { AnimatePresence, motion } from "framer-motion";
import { AdminUserRow, listUsers, updateUser, useCurrentUser } from "@/lib/auth";

export default function AdminPage() {
  const me = useCurrentUser();
  const [users, setUsers] = useState<AdminUserRow[] | null>(null);
  const [error, setError] = useState<string | null>(null);

  function refresh() {
    listUsers()
      .then(setUsers)
      .catch(() => setError("Akses ditolak — halaman ini khusus admin."));
  }

  useEffect(() => {
    if (me) refresh();
  }, [me]);

  if (me === undefined) return null;
  if (me && me.role !== "admin") {
    return <p className="text-sm text-text-muted">Halaman ini khusus admin.</p>;
  }
  if (error) return <p className="text-sm text-loss">{error}</p>;

  async function toggleActive(u: AdminUserRow) {
    await updateUser(u.id, { is_active: !u.is_active });
    refresh();
  }

  async function toggleRole(u: AdminUserRow) {
    await updateUser(u.id, { role: u.role === "admin" ? "user" : "admin" });
    refresh();
  }

  return (
    <motion.div initial={{ opacity: 0, y: 10 }} animate={{ opacity: 1, y: 0 }} transition={{ duration: 0.25 }}>
      <h1 className="mb-1 text-sm font-semibold text-text">Manajemen User</h1>
      <p className="mb-5 text-[11px] text-text-faint">
        Admin bisa kelola user & role. User biasa cuma bisa auto trade pakai akun Binance sendiri.
      </p>

      <div className="overflow-hidden rounded-xl border border-border bg-bg-panel">
        <table className="w-full text-left text-[12px]">
          <thead>
            <tr className="border-b border-border text-text-faint">
              <th className="px-4 py-2">Email</th>
              <th className="px-4 py-2">Role</th>
              <th className="px-4 py-2">Status</th>
              <th className="px-4 py-2">Binance Key</th>
              <th className="px-4 py-2" />
            </tr>
          </thead>
          <tbody>
            <AnimatePresence initial={false}>
              {users?.map((u, i) => (
                <motion.tr
                  key={u.id}
                  layout
                  initial={{ opacity: 0, y: -6 }}
                  animate={{ opacity: 1, y: 0, transition: { duration: 0.25, delay: Math.min(i, 8) * 0.04 } }}
                  exit={{ opacity: 0, transition: { duration: 0.15 } }}
                  className="border-b border-border-soft text-text"
                >
                  <td className="px-4 py-2">{u.email}</td>
                  <td className="px-4 py-2">
                    <span
                      className={`rounded-full px-2 py-0.5 text-[10px] font-semibold ${
                        u.role === "admin" ? "bg-brand/10 text-brand" : "bg-text-faint/10 text-text-muted"
                      }`}
                    >
                      {u.role.toUpperCase()}
                    </span>
                  </td>
                  <td className="px-4 py-2">
                    <span className={u.is_active ? "text-profit" : "text-loss"}>
                      {u.is_active ? "Aktif" : "Nonaktif"}
                    </span>
                  </td>
                  <td className="px-4 py-2 text-text-faint">{u.binance_configured ? "Terpasang" : "Belum"}</td>
                  <td className="space-x-2 px-4 py-2 text-right">
                    <button onClick={() => toggleRole(u)} className="cursor-pointer text-brand hover:underline">
                      {u.role === "admin" ? "Jadikan user" : "Jadikan admin"}
                    </button>
                    <button onClick={() => toggleActive(u)} className="cursor-pointer text-text-faint hover:underline">
                      {u.is_active ? "Nonaktifkan" : "Aktifkan"}
                    </button>
                  </td>
                </motion.tr>
              ))}
            </AnimatePresence>
          </tbody>
        </table>
      </div>
    </motion.div>
  );
}
