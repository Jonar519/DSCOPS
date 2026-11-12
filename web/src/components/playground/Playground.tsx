"use client";

/**
 * Pantalla del playground. Une el estado (useCompiler) con los componentes:
 *
 *   ┌ Editor ───────────────┐ ┌ Resultado ────────────┐
 *   │ ejemplos              │ │ veredicto             │
 *   │ código                │ │ hallazgos             │
 *   │ destinos · botones    │ │ archivos generados    │
 *   └───────────────────────┘ └───────────────────────┘
 */
import { AnimatePresence, motion } from "motion/react";
import Link from "next/link";
import { useEffect, useState } from "react";
import { useCompiler, type Compiler } from "@/hooks/useCompiler";
import { GITHUB_URL } from "@/lib/catalog";
import type { Diagnostic } from "@/lib/types";
import { Button } from "../ui/Button";
import { Frame } from "../ui/Frame";
import { IconAlert, IconCheck, IconError, IconGithub, IconPlay, IconShield, IconX } from "../ui/Icons";
import { Logo } from "../ui/Logo";
import { Artifacts } from "./Artifacts";
import { type EditorFocus, Editor } from "./Editor";
import { Findings } from "./Findings";
import { ApiStatus, SamplePicker, TargetPicker } from "./Toolbar";

export function Playground() {
  const compiler = useCompiler();
  const [focus, setFocus] = useState<EditorFocus | null>(null);
  const [activeKey, setActiveKey] = useState<string | null>(null);

  // Si el código cambia, la marca del hallazgo seleccionado ya no es fiable.
  useEffect(() => {
    setFocus(null);
    setActiveKey(null);
  }, [compiler.source]);

  // Atajos: Ctrl+Enter compila, Ctrl+Shift+Enter valida.
  const { compile, check } = compiler;
  useEffect(() => {
    function onKey(e: KeyboardEvent) {
      if (!(e.ctrlKey || e.metaKey) || e.key !== "Enter") return;
      e.preventDefault();
      if (e.shiftKey) void check();
      else void compile();
    }
    window.addEventListener("keydown", onKey);
    return () => window.removeEventListener("keydown", onKey);
  }, [compile, check]);

  function selectFinding(d: Diagnostic, key: string) {
    setActiveKey(key);
    setFocus({ diagnostic: d, nonce: Date.now() });
  }

  return (
    <div className="flex min-h-dvh flex-col lg:h-dvh">
      <Header compiler={compiler} />

      <AnimatePresence>
        {compiler.health === "offline" && <OfflineNotice />}
      </AnimatePresence>

      <main className="grid flex-1 gap-5 p-4 sm:p-5 lg:min-h-0 lg:grid-cols-[minmax(0,1.05fr)_minmax(0,1fr)]">
        {/* ---------------------------- Editor ---------------------------- */}
        <Frame label="app.dscops" className="flex min-h-0 flex-col">
          <div className="flex flex-wrap items-center justify-between gap-3 border-b border-line-soft px-4 py-2.5">
            <SamplePicker value={compiler.sampleId} onChange={compiler.loadSample} />
            <p className="text-xs text-pencil">Se valida solo mientras escribes</p>
          </div>

          <div className="min-h-0 flex-1">
            <Editor
              value={compiler.source}
              onChange={compiler.setSource}
              diagnostics={compiler.diagnostics}
              focus={focus}
            />
          </div>

          <div className="flex flex-col gap-3 border-t border-line-soft px-4 py-3 sm:flex-row sm:items-center sm:justify-between">
            <TargetPicker targets={compiler.targets} selected={compiler.selected} onToggle={compiler.toggleTarget} />
            <div className="flex shrink-0 gap-2 self-end sm:self-auto">
              <Button onClick={() => void compiler.check()} disabled={compiler.busy} title="Ctrl + Shift + Enter">
                <IconShield size={14} /> Validar
              </Button>
              <Button variant="primary" onClick={() => void compiler.compile()} disabled={compiler.busy} title="Ctrl + Enter">
                <IconPlay size={13} /> Compilar
              </Button>
            </div>
          </div>
        </Frame>

        {/* --------------------------- Resultado -------------------------- */}
        <Frame label="resultado" className="grid min-h-[640px] grid-rows-[auto_minmax(0,1fr)_minmax(0,1.15fr)] lg:min-h-0">
          <div>
          <Verdict compiler={compiler} />

          <AnimatePresence>
            {compiler.error && compiler.health !== "offline" && (
              <motion.div
                initial={{ opacity: 0, height: 0 }}
                animate={{ opacity: 1, height: "auto" }}
                exit={{ opacity: 0, height: 0 }}
                className="overflow-hidden"
              >
                <div className="mx-4 mb-3 flex items-start gap-2 rounded-md border border-fail/40 bg-fail/10 px-3 py-2 text-sm text-paper">
                  <IconError size={15} className="mt-0.5 shrink-0 text-fail" />
                  <span className="flex-1">{compiler.error}</span>
                  <button type="button" onClick={compiler.dismissError} aria-label="Cerrar" className="text-pencil hover:text-paper">
                    <IconX size={14} />
                  </button>
                </div>
              </motion.div>
            )}
          </AnimatePresence>
          </div>

          <Findings
            diagnostics={compiler.diagnostics}
            counts={compiler.counts}
            source={compiler.source}
            activeKey={activeKey}
            onSelect={selectFinding}
            pending={!compiler.hasResult && compiler.phase !== "failed"}
          />

          <div className="min-h-0 border-t border-line-soft">
            <Artifacts
              artifacts={compiler.artifacts}
              compiledOk={compiler.compiledOk}
              compiling={compiler.phase === "compiling"}
            />
          </div>
        </Frame>
      </main>

      <footer className="hidden px-5 pb-3 text-[11px] text-pencil/70 lg:block">
        Atajos: <Kbd>Ctrl</Kbd> + <Kbd>Enter</Kbd> compila, <Kbd>Ctrl</Kbd> + <Kbd>Shift</Kbd> + <Kbd>Enter</Kbd> valida.
        Haz clic en un hallazgo para ir a la línea.
      </footer>
    </div>
  );
}

/* ------------------------------------------------------------------------ */

function Header({ compiler }: { compiler: Compiler }) {
  return (
    <header className="flex h-14 shrink-0 items-center justify-between gap-4 border-b border-line-soft bg-ink/80 px-4 backdrop-blur-md sm:px-5">
      <div className="flex items-center gap-4">
        <Logo />
        <span className="hidden h-5 w-px bg-line sm:block" />
        <h1 className="hidden text-sm text-pencil sm:block">Playground</h1>
      </div>
      <div className="flex items-center gap-4">
        <ApiStatus health={compiler.health} />
        <nav className="hidden items-center gap-1 text-sm md:flex">
          <Link href="/" className="rounded px-2.5 py-1.5 text-pencil hover:text-paper">Inicio</Link>
          <a href="/docs" className="rounded px-2.5 py-1.5 text-pencil hover:text-paper">API</a>
          <a href={GITHUB_URL} target="_blank" rel="noreferrer" aria-label="GitHub" className="rounded p-1.5 text-pencil hover:text-paper">
            <IconGithub size={17} />
          </a>
        </nav>
      </div>
    </header>
  );
}

function OfflineNotice() {
  return (
    <motion.div
      initial={{ opacity: 0, height: 0 }}
      animate={{ opacity: 1, height: "auto" }}
      exit={{ opacity: 0, height: 0 }}
      className="overflow-hidden border-b border-fail/30 bg-fail/[0.08]"
    >
      <p className="px-5 py-2.5 text-sm text-paper">
        <IconAlert size={14} className="mr-2 inline text-fail" />
        No hay conexión con la API de DSCOPS. Arráncala en otra terminal con{" "}
        <code className="rounded bg-ink-deep px-1.5 py-0.5 font-mono text-[13px] text-amber">uv run dscops serve</code>{" "}
        y recarga la página.
      </p>
    </motion.div>
  );
}

/** Frase grande que resume el resultado del último análisis. */
function Verdict({ compiler }: { compiler: Compiler }) {
  const { phase, verdict, counts, artifacts, compiledOk } = compiler;

  let tone: "busy" | "ok" | "warn" | "error" = "busy";
  let title = "Esperando código";
  let detail = "Escribe o carga un ejemplo.";

  if (phase === "checking") {
    title = "Validando…";
    detail = "Sintaxis, semántica y reglas de seguridad.";
  } else if (phase === "compiling") {
    title = "Compilando…";
    detail = "Generando los archivos de cada destino.";
  } else if (phase === "failed") {
    tone = "error";
    title = "No se pudo analizar";
    detail = "Revisa la conexión con la API.";
  } else if (verdict === "errors") {
    tone = "error";
    title = counts.error === 1 ? "Hay 1 error que corregir" : `Hay ${counts.error} errores que corregir`;
    detail = "Mientras haya errores no se generan archivos.";
  } else if (verdict === "warnings") {
    tone = "warn";
    title = compiledOk ? `Compilado con observaciones` : "Válido, con observaciones";
    detail = compiledOk ? `${artifacts.length} archivo(s) generado(s). Revisa los avisos.` : "Se puede compilar. Revisa los avisos.";
  } else if (verdict === "ok") {
    tone = "ok";
    title = compiledOk ? "Compilado sin hallazgos" : "Todo en orden";
    detail = compiledOk ? `${artifacts.length} archivo(s) generado(s).` : "Listo para compilar.";
  }

  const ICON = {
    busy: <span className="size-4 animate-spin rounded-full border-2 border-line border-t-amber" />,
    ok: <IconCheck size={16} strokeWidth={3} className="text-pass" />,
    warn: <IconAlert size={16} className="text-amber" />,
    error: <IconError size={16} className="text-fail" />,
  }[tone];

  const RING = { busy: "border-line", ok: "border-pass/50 bg-pass/10", warn: "border-amber/50 bg-amber/10", error: "border-fail/50 bg-fail/10" }[tone];

  return (
    <div className="flex items-center gap-3 px-4 pb-3 pt-5">
      <AnimatePresence mode="wait">
        <motion.span
          key={tone}
          initial={{ scale: 0.6, opacity: 0 }}
          animate={{ scale: 1, opacity: 1 }}
          exit={{ scale: 0.6, opacity: 0 }}
          transition={{ type: "spring", stiffness: 400, damping: 22 }}
          className={`grid size-9 shrink-0 place-items-center rounded-full border ${RING}`}
        >
          {ICON}
        </motion.span>
      </AnimatePresence>
      <div className="min-w-0" aria-live="polite">
        <AnimatePresence mode="wait">
          <motion.p
            key={title}
            initial={{ opacity: 0, y: 4 }}
            animate={{ opacity: 1, y: 0 }}
            exit={{ opacity: 0, y: -4 }}
            transition={{ duration: 0.15 }}
            className="text-lg font-semibold leading-tight tracking-tight"
          >
            {title}
          </motion.p>
        </AnimatePresence>
        <p className="text-sm text-pencil">{detail}</p>
      </div>
    </div>
  );
}

function Kbd({ children }: { children: React.ReactNode }) {
  return <kbd className="rounded border border-line bg-ink-deep px-1 py-px font-mono text-[10px] text-pencil">{children}</kbd>;
}
