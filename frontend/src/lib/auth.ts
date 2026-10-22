"use client";

import { useEffect, useState } from "react";

const API_BASE = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000";

async function authFetch<T>(path: string, init?: RequestInit): Promise<T> {
  const res = await fetch(`${API_BASE}${path}`, {
    credentials: "include",
    headers: { "Content-Type": "application/json" },
    ...init,
  });
  if (!res.ok) throw new Error(`${path} -> HTTP ${res.status}`);
  return res.json();
}

export type CurrentUser = { email: string; role: "user" | "admin" };

export function login(email: string, password: string) {
  return authFetch<CurrentUser>("/api/v1/auth/login", { method: "POST", body: JSON.stringify({ email, password }) });
}

export function register(email: string, password: string) {
  return authFetch<CurrentUser>("/api/v1/auth/register", {
    method: "POST",
    body: JSON.stringify({ email, password }),
  });
}

export function logout() {
  return authFetch<{ ok: boolean }>("/api/v1/auth/logout", { method: "POST" });
}

export type BinanceCredentialsStatus = { configured: boolean; api_key_last4: string | null };

export function getBinanceCredentials() {
  return authFetch<BinanceCredentialsStatus>("/api/v1/auth/binance-credentials");
}

export function saveBinanceCredentials(apiKey: string, apiSecret: string) {
  return authFetch<BinanceCredentialsStatus>("/api/v1/auth/binance-credentials", {
    method: "PUT",
    body: JSON.stringify({ api_key: apiKey, api_secret: apiSecret }),
  });
}

export type AdminUserRow = {
  id: string;
  email: string;
  role: "user" | "admin";
  is_active: boolean;
  binance_configured: boolean;
  created_at: string;
};

export function listUsers() {
  return authFetch<AdminUserRow[]>("/api/v1/admin/users");
}

export function updateUser(id: string, patch: { role?: "user" | "admin"; is_active?: boolean }) {
  return authFetch<AdminUserRow>(`/api/v1/admin/users/${id}`, { method: "PATCH", body: JSON.stringify(patch) });
}

/** null = not logged in, undefined = still checking. */
export function useCurrentUser() {
  const [user, setUser] = useState<CurrentUser | null | undefined>(undefined);

  useEffect(() => {
    let cancelled = false;
    authFetch<CurrentUser>("/api/v1/auth/me")
      .then((u) => !cancelled && setUser(u))
      .catch(() => !cancelled && setUser(null));
    return () => {
      cancelled = true;
    };
  }, []);

  return user;
}
