"use client";

/**
 * Editor de código ligero, sin librerías.
 *
 * Truco: hay un <textarea> transparente encima de un bloque coloreado.
 *   - El textarea recibe el teclado, el cursor y la selección.
 *   - Debajo se pinta el mismo texto con colores y subrayados de error.
 * Ambos usan exactamente la misma fuente, tamaño, interlineado y padding,
 * así las letras quedan alineadas. Al hacer scroll movemos la capa de abajo.
 */
import { motion } from "motion/react";
import { useEffect, useMemo, useRef, useState, type KeyboardEvent } from "react";
import { highlight, TOKEN_CLASS } from "@/lib/highlight";
import type { Diagnostic, Severity } from "@/lib/types";

const LINE_HEIGHT = 22; // px, debe coincidir en textarea, código y gutter
const PAD_Y = 16;
const PAD_X = 16;

const LINE_BAND: Record<Severity, string> = {
  error: "bg-fail/10 shadow-[inset_2px_0_0_var(--color-fail)]",
  warning: "bg-amber/10 shadow-[inset_2px_0_0_var(--color-amber)]",
  info: "bg-sky/10 shadow-[inset_2px_0_0_var(--color-sky)]",
};

export interface EditorFocus {
  diagnostic: Diagnostic;
  /** Cambia en cada clic para poder saltar dos veces al mismo hallazgo. */
  nonce: number;
}

interface EditorProps {
  value: string;
  onChange: (value: string) => void;
  diagnostics: Diagnostic[];
  focus: EditorFocus | null;
}

export function Editor({ value, onChange, diagnostics, focus }: EditorProps) {
  const textareaRef = useRef<HTMLTextAreaElement>(null);
  const [scroll, setScroll] = useState({ top: 0, left: 0 });
  const [cursorLine, setCursorLine] = useState(1);

  const lines = useMemo(() => highlight(value, "dscops"), [value]);

  // Solo los hallazgos con posición se pueden dibujar en el editor.
  const marks = diagnostics.filter((d) => d.line && d.line <= lines.length);
  const focusedLine = focus?.diagnostic.line ?? null;

  /* Saltar a un hallazgo: seleccionar el fragmento y centrarlo. */
  useEffect(() => {
    const el = textareaRef.current;
    const d = focus?.diagnostic;
    if (!el || !d?.line) return;

    const all = value.split("\n");
    const lineIndex = Math.min(d.line, all.length) - 1;
    const lineStart = all.slice(0, lineIndex).reduce((sum, l) => sum + l.length + 1, 0);
    const col = Math.max(0, (d.column ?? 1) - 1);
    const len = Math.max(1, d.length ?? 1);
    const end = Math.min(all[lineIndex].length, col + len);

    el.focus();
    el.setSelectionRange(lineStart + col, lineStart + Math.max(end, col));
    el.scrollTop = Math.max(0, PAD_Y + lineIndex * LINE_HEIGHT - el.clientHeight / 3);
    setCursorLine(lineIndex + 1);
    // `value` no va en las dependencias a propósito: solo saltamos cuando cambia el foco.
  }, [focus]);

  function updateCursorLine() {
    const el = textareaRef.current;
    if (!el) return;
    setCursorLine(value.slice(0, el.selectionStart).split("\n").length);
  }

  /* Tab inserta dos espacios en lugar de salir del editor. */
  function handleKeyDown(event: KeyboardEvent<HTMLTextAreaElement>) {
    if (event.key !== "Tab" || event.shiftKey) return;
    event.preventDefault();
    const el = event.currentTarget;
    const { selectionStart: start, selectionEnd: end } = el;
    onChange(value.slice(0, start) + "  " + value.slice(end));
    requestAnimationFrame(() => el.setSelectionRange(start + 2, start + 2));
  }

  const gutterWidth = Math.max(2, String(lines.length).length) + 2; // en ch

  return (
    <div className="relative flex h-[clamp(360px,58vh,600px)] font-mono lg:h-full text-[13px]">
      {/* Números de línea */}
      <div
        aria-hidden="true"
        className="relative shrink-0 select-none overflow-hidden border-r border-line-soft bg-ink/40 text-right text-pencil/45"
        style={{ width: `${gutterWidth}ch` }}
      >
        <div style={{ transform: `translateY(${-scroll.top}px)`, paddingTop: PAD_Y }}>
          {lines.map((_, i) => {
            const n = i + 1;
            const mark = marks.find((d) => d.line === n);
            return (
              <div
                key={n}
                style={{ height: LINE_HEIGHT, lineHeight: `${LINE_HEIGHT}px` }}
                className={`pr-2.5 transition-colors ${
                  n === focusedLine ? "text-paper" : n === cursorLine ? "text-pencil" : ""
                }`}
              >
                {mark ? <span className={dotColor(mark.severity)}>●</span> : n}
              </div>
            );
          })}
        </div>
      </div>

      <div className="relative min-w-0 flex-1 overflow-hidden">
        {/* Bandas de fondo: línea del cursor y línea del hallazgo activo */}
        <div aria-hidden="true" className="pointer-events-none absolute inset-0">
          <div style={{ transform: `translateY(${-scroll.top}px)` }}>
            <div
              className="absolute inset-x-0 bg-ink-soft/50"
              style={{ top: PAD_Y + (cursorLine - 1) * LINE_HEIGHT, height: LINE_HEIGHT }}
            />
            {focus?.diagnostic.line && (
              <motion.div
                key={focus.nonce}
                className={`absolute inset-x-0 ${LINE_BAND[focus.diagnostic.severity]}`}
                style={{ top: PAD_Y + (focus.diagnostic.line - 1) * LINE_HEIGHT, height: LINE_HEIGHT }}
                initial={{ opacity: 0, scaleX: 0.96 }}
                animate={{ opacity: 1, scaleX: 1 }}
                transition={{ duration: 0.25 }}
              />
            )}
          </div>
        </div>

        {/* Texto coloreado + subrayados ondulados */}
        <div aria-hidden="true" className="pointer-events-none absolute inset-0">
          <div
            className="relative"
            style={{
              transform: `translate(${-scroll.left}px, ${-scroll.top}px)`,
              padding: `${PAD_Y}px ${PAD_X}px`,
            }}
          >
            {lines.map((tokens, i) => (
              <div key={i} className="whitespace-pre" style={{ height: LINE_HEIGHT, lineHeight: `${LINE_HEIGHT}px` }}>
                {tokens.map((t, j) => (
                  <span key={j} className={TOKEN_CLASS[t.type]}>{t.text}</span>
                ))}
              </div>
            ))}
            {marks.map((d, i) => {
              const { start, length } = markRange(value, d);
              return (
                <span
                  key={`${d.code}-${i}`}
                  className={`squiggle squiggle-${d.severity} absolute h-[4px]`}
                  style={{
                    top: PAD_Y + (d.line as number) * LINE_HEIGHT - 4,
                    left: `calc(${PAD_X}px + ${start}ch)`,
                    width: `${length}ch`,
                  }}
                />
              );
            })}
          </div>
        </div>

        {/* El textarea real: invisible, pero recibe todo lo que escribes */}
        <textarea
          ref={textareaRef}
          value={value}
          onChange={(e) => onChange(e.target.value)}
          onKeyDown={handleKeyDown}
          onKeyUp={updateCursorLine}
          onClick={updateCursorLine}
          onSelect={updateCursorLine}
          onScroll={(e) => setScroll({ top: e.currentTarget.scrollTop, left: e.currentTarget.scrollLeft })}
          spellCheck={false}
          autoCapitalize="off"
          autoComplete="off"
          autoCorrect="off"
          aria-label="Código DSCOPS"
          wrap="off"
          className="scroll-thin absolute inset-0 h-full w-full resize-none overflow-auto whitespace-pre bg-transparent text-transparent caret-amber outline-none selection:bg-amber/30"
          style={{ padding: `${PAD_Y}px ${PAD_X}px`, lineHeight: `${LINE_HEIGHT}px`, tabSize: 2 }}
        />
      </div>
    </div>
  );
}

function dotColor(severity: Severity) {
  return severity === "error" ? "text-fail" : severity === "warning" ? "text-amber" : "text-sky";
}

/** Columna inicial (base 0) y ancho del subrayado de un hallazgo. */
function markRange(source: string, d: Diagnostic) {
  const text = source.split("\n")[(d.line as number) - 1] ?? "";
  if (d.column) return { start: d.column - 1, length: Math.max(1, d.length ?? 1) };
  // Sin columna: subrayamos el contenido de la línea, sin la sangría.
  const indent = text.length - text.trimStart().length;
  return { start: indent, length: Math.max(1, text.trim().length) };
}
