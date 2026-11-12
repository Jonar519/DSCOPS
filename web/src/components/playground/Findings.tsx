"use client";

/** Lista de hallazgos (errores, advertencias y avisos) del último análisis. */
import { AnimatePresence, motion } from "motion/react";
import { useMemo, useState } from "react";
import { plural } from "@/lib/catalog";
import type { Diagnostic, Severity } from "@/lib/types";
import { IconCheck } from "../ui/Icons";
import { SEVERITY_STYLE, SeverityIcon } from "../ui/SeverityBadge";

const ORDER: Severity[] = ["error", "warning", "info"];

interface FindingsProps {
  diagnostics: Diagnostic[];
  counts: Record<Severity, number>;
  source: string;
  activeKey: string | null;
  onSelect: (diagnostic: Diagnostic, key: string) => void;
  /** true mientras no se ha recibido ningún resultado. */
  pending: boolean;
}

export function keyOf(d: Diagnostic) {
  return `${d.code}:${d.line ?? 0}:${d.column ?? 0}:${d.message}`;
}

export function Findings({ diagnostics, counts, source, activeKey, onSelect, pending }: FindingsProps) {
  const [hidden, setHidden] = useState<Severity[]>([]);

  const sorted = useMemo(
    () =>
      [...diagnostics].sort(
        (a, b) => (a.line ?? 0) - (b.line ?? 0) || (a.column ?? 0) - (b.column ?? 0) || a.code.localeCompare(b.code),
      ),
    [diagnostics],
  );
  const visible = sorted.filter((d) => !hidden.includes(d.severity));
  const lines = source.split("\n");

  const toggle = (s: Severity) => setHidden((h) => (h.includes(s) ? h.filter((x) => x !== s) : [...h, s]));

  return (
    <div className="flex min-h-0 flex-col">
      {/* Filtros por severidad: también funcionan como contadores */}
      <div className="flex flex-wrap gap-2 px-4 pb-3" role="group" aria-label="Filtrar por severidad">
        {ORDER.map((s) => {
          const style = SEVERITY_STYLE[s];
          const on = !hidden.includes(s);
          return (
            <button
              key={s}
              type="button"
              onClick={() => toggle(s)}
              aria-pressed={on}
              className={`inline-flex items-center gap-1.5 rounded border px-2.5 py-1 text-xs font-medium transition-all ${
                on ? `${style.text} ${style.border} ${style.bg}` : "border-line-soft text-pencil/50 line-through"
              }`}
            >
              <SeverityIcon severity={s} size={12} />
              <motion.span key={counts[s]} initial={{ y: -6, opacity: 0 }} animate={{ y: 0, opacity: 1 }}>
                {plural(counts[s], s)}
              </motion.span>
            </button>
          );
        })}
      </div>

      <div className="scroll-thin min-h-0 flex-1 overflow-y-auto px-4 pb-4">
        {pending ? (
          <SkeletonList />
        ) : diagnostics.length === 0 ? (
          <motion.div
            initial={{ opacity: 0, scale: 0.97 }}
            animate={{ opacity: 1, scale: 1 }}
            className="flex items-center gap-3 rounded-md border border-pass/30 bg-pass/[0.07] p-4"
          >
            <span className="grid size-8 shrink-0 place-items-center rounded-full bg-pass/15 text-pass">
              <IconCheck size={16} strokeWidth={3} />
            </span>
            <div>
              <p className="font-medium text-paper">Sin hallazgos</p>
              <p className="text-sm text-pencil">La sintaxis, la semántica y las diez reglas pasaron.</p>
            </div>
          </motion.div>
        ) : (
          <ul className="space-y-2">
            <AnimatePresence initial={false} mode="popLayout">
              {visible.map((d) => {
                const key = keyOf(d);
                return (
                  <motion.li
                    key={key}
                    layout
                    initial={{ opacity: 0, y: 6 }}
                    animate={{ opacity: 1, y: 0 }}
                    exit={{ opacity: 0, scale: 0.98 }}
                    transition={{ duration: 0.2 }}
                  >
                    <FindingCard
                      diagnostic={d}
                      lineText={d.line ? (lines[d.line - 1] ?? "") : ""}
                      active={key === activeKey}
                      onSelect={() => onSelect(d, key)}
                    />
                  </motion.li>
                );
              })}
            </AnimatePresence>
            {visible.length === 0 && (
              <li className="rounded-md border border-dashed border-line p-4 text-center text-sm text-pencil">
                Todos los hallazgos están ocultos por los filtros.
              </li>
            )}
          </ul>
        )}
      </div>
    </div>
  );
}

function FindingCard({
  diagnostic: d,
  lineText,
  active,
  onSelect,
}: {
  diagnostic: Diagnostic;
  lineText: string;
  active: boolean;
  onSelect: () => void;
}) {
  const style = SEVERITY_STYLE[d.severity];
  const where = d.line ? `Línea ${d.line}${d.column ? `, columna ${d.column}` : ""}` : "Sin ubicación";

  return (
    <button
      type="button"
      onClick={onSelect}
      disabled={!d.line}
      className={`group w-full rounded-md border bg-ink/40 p-3 text-left transition-colors disabled:cursor-default ${
        active ? `${style.border} ${style.bg}` : "border-line-soft hover:border-line hover:bg-ink-soft/40"
      }`}
    >
      <div className="flex items-start gap-2.5">
        <span className="mt-0.5"><SeverityIcon severity={d.severity} /></span>
        <div className="min-w-0 flex-1">
          <div className="flex flex-wrap items-baseline justify-between gap-x-3 gap-y-1">
            <p className="text-sm leading-snug text-paper">{d.message}</p>
            <span className="shrink-0 font-mono text-[11px] text-pencil">{d.code}</span>
          </div>

          {d.line && lineText && <Snippet line={d.line} text={lineText} diagnostic={d} />}

          {d.hint && (
            <p className="mt-2 text-[13px] leading-snug text-pencil">
              <span className="text-amber">Cómo arreglarlo: </span>
              {d.hint}
            </p>
          )}

          <p className="mt-2 text-[11px] text-pencil/70 group-enabled:group-hover:text-pencil">
            {where}
            {d.line && <span className="ml-1">· clic para verlo en el editor</span>}
          </p>
        </div>
      </div>
    </button>
  );
}

/** La línea afectada, con el fragmento marcado y un ^^^ debajo. */
function Snippet({ line, text, diagnostic }: { line: number; text: string; diagnostic: Diagnostic }) {
  const indent = text.length - text.trimStart().length;
  const start = diagnostic.column ? diagnostic.column - 1 : indent;
  const length = diagnostic.column ? Math.max(1, diagnostic.length ?? 1) : Math.max(1, text.trim().length);

  return (
    <pre className="scroll-thin mt-2 overflow-x-auto rounded border border-line-soft bg-ink-deep px-2.5 py-1.5 font-mono text-[11.5px] leading-[1.55]">
      <div>
        <span className="mr-[1ch] select-none text-pencil/50">{line}</span>
        <span className="text-paper/80">{text.slice(0, start)}</span>
        <span className="text-paper underline decoration-wavy underline-offset-[3px]" style={{ textDecorationColor: `var(--color-${diagnostic.severity === "error" ? "fail" : diagnostic.severity === "warning" ? "amber" : "sky"})` }}>
          {text.slice(start, start + length) || " "}
        </span>
        <span className="text-paper/80">{text.slice(start + length)}</span>
      </div>
    </pre>
  );
}

function SkeletonList() {
  return (
    <div className="space-y-2" aria-hidden="true">
      {[0, 1, 2].map((i) => (
        <div key={i} className="h-16 animate-pulse rounded-md border border-line-soft bg-ink-soft/30" />
      ))}
    </div>
  );
}
