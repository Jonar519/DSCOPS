import Link from "next/link";

export function Logo() {
  return (
    <Link href="/" className="group inline-flex items-center gap-2.5" aria-label="DSCOPS, inicio">
      <span className="grid size-8 place-items-center rounded-md border border-line bg-ink-deep font-mono text-sm font-semibold text-amber transition-colors group-hover:border-amber/60">
        {"{}"}
      </span>
      <span className="text-[15px] font-semibold tracking-tight">DSCOPS</span>
    </Link>
  );
}
