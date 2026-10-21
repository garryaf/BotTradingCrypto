import type { Metadata } from "next";
import "./globals.css";
import { AppHeader } from "@/components/AppHeader";

export const metadata: Metadata = {
  title: "AUTO-TRADE AA — Control Center",
  description: "Hermes Multi-Agent Orchestrator · Deterministic Risk Gate · Paper Trading",
};

export default function RootLayout({
  children,
}: Readonly<{
  children: React.ReactNode;
}>) {
  return (
    <html lang="id" className="dark">
      <body className="antialiased">
        <div className="mx-auto min-h-screen max-w-[1400px] px-5 py-5">
          <AppHeader />
          {children}
        </div>
      </body>
    </html>
  );
}
