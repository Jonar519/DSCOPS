import type { Severity } from "@/lib/types";
import { IconAlert, IconError, IconInfo } from "./Icons";

export const SEVERITY_STYLE: Record<Severity, { text: string; border: string; bg: string; label: string }> = {
  error: { text: "text-fail", border: "border-fail/40", bg: "bg-fail/10", label: "Error" },
  warning: { text: "text-amber", border: "border-amber/40", bg: "bg-amber/10", label: "Advertencia" },
  info: { text: "text-sky", border: "border-sky/40", bg: "bg-sky/10", label: "Aviso" },
};

export function SeverityIcon({ severity, size = 15 }: { severity: Severity; size?: number }) {
  const className = SEVERITY_STYLE[severity].text;
  if (severity === "error") return <IconError size={size} className={className} />;
  if (severity === "warning") return <IconAlert size={size} className={className} />;
  return <IconInfo size={size} className={className} />;
}

export function SeverityBadge({ severity }: { severity: Severity }) {
  const s = SEVERITY_STYLE[severity];
  return (
    <span className={`inline-flex items-center gap-1.5 rounded border px-2 py-0.5 text-xs font-medium ${s.text} ${s.border} ${s.bg}`}>
      <SeverityIcon severity={severity} size={12} />
      {s.label}
    </span>
  );
}
