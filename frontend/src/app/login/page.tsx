"use client";

import { useState } from "react";
import { useRouter } from "next/navigation";
import { motion } from "framer-motion";
import { Eye, EyeOff } from "lucide-react";
import { login } from "@/lib/auth";

export default function LoginPage() {
  const router = useRouter();
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [showPassword, setShowPassword] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [pending, setPending] = useState(false);

  async function onSubmit(e: React.FormEvent) {
    e.preventDefault();
    setError(null);
    setPending(true);
    try {
      await login(email, password);
      router.push("/");
      router.refresh();
    } catch {
      setError("Email atau password salah.");
    } finally {
      setPending(false);
    }
  }

  return (
    <div className="flex min-h-screen items-center justify-center px-5">
      <motion.form
        initial={{ opacity: 0, y: 10 }}
        animate={{ opacity: 1, y: 0 }}
        transition={{ duration: 0.25 }}
        onSubmit={onSubmit}
        className="w-full max-w-sm rounded-xl border border-border bg-bg-panel p-6"
      >
        <h1 className="mb-1 text-sm font-semibold text-text">Masuk ke AUTO-TRADE AA</h1>
        <p className="mb-5 text-[11px] text-text-faint">Setiap akun punya portofolio paper trading sendiri.</p>

        <label className="mb-1 block text-[11px] text-text-muted">Email</label>
        <input
          type="email"
          required
          autoComplete="email"
          value={email}
          onChange={(e) => setEmail(e.target.value)}
          className="mb-3 w-full rounded-md border border-border bg-bg-panel-raised px-3 py-2 text-sm text-text outline-none transition-colors focus:border-brand"
        />

        <label className="mb-1 block text-[11px] text-text-muted">Password</label>
        <div className="relative mb-4">
          <input
            type={showPassword ? "text" : "password"}
            required
            autoComplete="current-password"
            value={password}
            onChange={(e) => setPassword(e.target.value)}
            className="w-full rounded-md border border-border bg-bg-panel-raised px-3 py-2 pr-9 text-sm text-text outline-none transition-colors focus:border-brand"
          />
          <button
            type="button"
            onClick={() => setShowPassword((v) => !v)}
            aria-label={showPassword ? "Sembunyikan password" : "Tampilkan password"}
            className="absolute right-2.5 top-1/2 -translate-y-1/2 cursor-pointer text-text-faint hover:text-text-muted"
          >
            {showPassword ? <EyeOff size={14} /> : <Eye size={14} />}
          </button>
        </div>

        {error && (
          <motion.p initial={{ opacity: 0 }} animate={{ opacity: 1 }} className="mb-3 text-[11px] text-loss">
            {error}
          </motion.p>
        )}

        <button
          type="submit"
          disabled={pending}
          className="w-full cursor-pointer rounded-md bg-brand px-3 py-2 text-sm font-medium text-white transition-opacity hover:opacity-90 disabled:cursor-not-allowed disabled:opacity-50"
        >
          {pending ? "Masuk..." : "Masuk"}
        </button>
      </motion.form>
    </div>
  );
}
