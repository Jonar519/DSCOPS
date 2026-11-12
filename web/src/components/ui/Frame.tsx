import type { ReactNode } from "react";

/**
 * Panel con marcas de registro en las esquinas, como en un plano técnico.
 * Es el elemento visual que identifica a DSCOPS.
 */
export function Frame({
  children,
  className = "",
  label,
}: {
  children: ReactNode;
  className?: string;
  /** Texto pequeño en la esquina superior, como el rótulo de un plano. */
  label?: string;
}) {
  return (
    <div className={`relative rounded-lg border border-line bg-ink-deep/85 backdrop-blur-sm ${className}`}>
      <Corner className="-left-[7px] -top-[7px]" />
      <Corner className="-right-[7px] -top-[7px]" />
      <Corner className="-bottom-[7px] -left-[7px]" />
      <Corner className="-bottom-[7px] -right-[7px]" />
      {label && (
        <span className="absolute -top-2.5 left-4 bg-ink px-1.5 font-mono text-[11px] text-pencil">{label}</span>
      )}
      {children}
    </div>
  );
}

function Corner({ className }: { className: string }) {
  return (
    <svg
      aria-hidden="true"
      width="14"
      height="14"
      viewBox="0 0 14 14"
      className={`pointer-events-none absolute text-pencil/60 ${className}`}
    >
      <path d="M7 0v14M0 7h14" stroke="currentColor" strokeWidth="1" />
    </svg>
  );
}
