"use client";

/** Pestañas con los archivos generados por la última compilación. */
import { AnimatePresence, motion } from "motion/react";
import { useEffect, useState } from "react";
import { languageFor } from "@/lib/highlight";
import type { Artifact } from "@/lib/types";
import { Code } from "../ui/Code";
import { IconCheck, IconCopy, IconDownload, IconFile } from "../ui/Icons";

interface ArtifactsProps {
  artifacts: Artifact[];
  /** null = aún no se ha compilado; false = la compilación tuvo errores. */
  compiledOk: boolean | null;
  compiling: boolean;
}

export function Artifacts({ artifacts, compiledOk, compiling }: ArtifactsProps) {
  const [active, setActive] = useState(0);
  const [copied, setCopied] = useState(false);

  // Al llegar una compilación nueva, volver a la primera pestaña.
  useEffect(() => setActive(0), [artifacts]);

  const current = artifacts[active];

  async function copy() {
    if (!current) return;
    await navigator.clipboard.writeText(current.content);
    setCopied(true);
    setTimeout(() => setCopied(false), 1400);
  }

  function download() {
    if (!current) return;
    const blob = new Blob([current.content], { type: "text/plain;charset=utf-8" });
    const url = URL.createObjectURL(blob);
    const link = document.createElement("a");
    link.href = url;
    link.download = current.path.split("/").pop() ?? "artifact.txt";
    link.click();
    URL.revokeObjectURL(url);
  }

  if (!artifacts.length) {
    return (
      <div className="grid h-full min-h-[200px] place-items-center p-6 text-center">
        {compiling ? (
          <p className="flex items-center gap-2 text-sm text-pencil">
            <span className="size-3 animate-spin rounded-full border-2 border-line border-t-amber" />
            Generando archivos…
          </p>
        ) : compiledOk === false ? (
          <div className="max-w-xs">
            <p className="font-medium text-fail">No se generaron archivos</p>
            <p className="mt-1 text-sm text-pencil">Corrige los errores de la lista y vuelve a compilar.</p>
          </div>
        ) : (
          <div className="max-w-xs">
            <IconFile size={22} className="mx-auto mb-3 text-pencil/50" />
            <p className="text-sm text-pencil">
              Elige los destinos y pulsa <span className="text-paper">Compilar</span> para ver aquí los archivos generados.
            </p>
          </div>
        )}
      </div>
    );
  }

  return (
    <div className="flex h-full min-h-0 flex-col">
      <div className="flex items-center justify-between gap-2 border-b border-line-soft pr-2">
        <div role="tablist" aria-label="Archivos generados" className="scroll-thin flex overflow-x-auto">
          {artifacts.map((a, i) => (
            <button
              key={a.path}
              type="button"
              role="tab"
              aria-selected={i === active}
              onClick={() => setActive(i)}
              className={`relative whitespace-nowrap px-4 py-2.5 font-mono text-xs transition-colors ${
                i === active ? "text-paper" : "text-pencil hover:text-paper"
              }`}
            >
              {a.path}
              {i === active && (
                <motion.span
                  layoutId="artifact-tab"
                  className="absolute inset-x-2 bottom-0 h-0.5 rounded-full bg-amber"
                  transition={{ type: "spring", stiffness: 500, damping: 38 }}
                />
              )}
            </button>
          ))}
        </div>
        <div className="flex shrink-0 gap-1">
          <IconAction onClick={copy} label={copied ? "Copiado" : "Copiar"}>
            {copied ? <IconCheck size={14} className="text-pass" /> : <IconCopy size={14} />}
          </IconAction>
          <IconAction onClick={download} label="Descargar">
            <IconDownload size={14} />
          </IconAction>
        </div>
      </div>

      <div className="scroll-thin relative min-h-0 flex-1 overflow-auto">
        <AnimatePresence mode="wait">
          {current && (
            <motion.div
              key={current.path}
              initial={{ opacity: 0, x: 8 }}
              animate={{ opacity: 1, x: 0 }}
              exit={{ opacity: 0, x: -8 }}
              transition={{ duration: 0.18 }}
              className="p-4"
            >
              <Code source={current.content} language={languageFor(current.path)} />
            </motion.div>
          )}
        </AnimatePresence>
      </div>
    </div>
  );
}

function IconAction({ onClick, label, children }: { onClick: () => void; label: string; children: React.ReactNode }) {
  return (
    <button
      type="button"
      onClick={onClick}
      title={label}
      className="inline-flex items-center gap-1.5 rounded px-2 py-1.5 text-xs text-pencil transition-colors hover:bg-ink-soft hover:text-paper"
    >
      {children}
      <span className="hidden sm:inline">{label}</span>
    </button>
  );
}
