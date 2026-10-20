import { PlugZap } from "lucide-react";

export function NotConnected({
  title,
  detail,
  compact = false,
}: {
  title: string;
  detail: string;
  compact?: boolean;
}) {
  return (
    <div
      className={`flex flex-col items-center justify-center gap-2 rounded-lg border border-dashed border-border-soft text-center ${
        compact ? "px-4 py-8" : "px-6 py-16"
      }`}
    >
      <PlugZap size={compact ? 18 : 22} className="text-text-faint" />
      <p className="text-xs font-medium text-text-muted">{title}</p>
      <p className="max-w-xs text-[11px] text-text-faint">{detail}</p>
    </div>
  );
}
