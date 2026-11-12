"use client";

/**
 * Demo animada del hero: se escribe un archivo .dscops, pasa por las cuatro
 * fases del compilador y aparece el compose.yaml generado.
 * Es la única animación automática de la página; con "reducir movimiento"
 * se muestra directamente el resultado final.
 */
import { AnimatePresence, motion, useReducedMotion } from "motion/react";
import { useEffect, useState } from "react";
import { Code } from "../ui/Code";
import { Frame } from "../ui/Frame";
import { IconCheck, IconInfo, IconRefresh } from "../ui/Icons";

const SOURCE = `service api {
  image: "python:3.12-slim"
  port: 8000
  replicas: 2
  env: { DB_URL: secret("db_url") }
  expose: public
  user: "10001:10001"
}

database main {
  engine: postgres
  expose: private
}

api -> main`;

const OUTPUT = `services:
  api:
    image: python:3.12-slim
    user: 10001:10001
    security_opt:
    - no-new-privileges:true
    environment:
      DB_URL: \${DB_URL}
    ports:
    - 8000-8001:8000
    deploy:
      replicas: 2
    depends_on:
      main:
        condition: service_healthy`;

const STAGES = ["Sintaxis", "Semántica", "Seguridad", "Generación"];

type Step = { kind: "typing"; chars: number } | { kind: "stages"; done: number } | { kind: "output" };

const TYPE_SPEED_MS = 16;
const STAGE_MS = 480;

export function CompileDemo() {
  const reduceMotion = useReducedMotion();
  const [step, setStep] = useState<Step>({ kind: "typing", chars: 0 });
  const [run, setRun] = useState(0);

  useEffect(() => {
    if (reduceMotion) {
      setStep({ kind: "output" });
      return;
    }
    let cancelled = false;
    const timers: ReturnType<typeof setTimeout>[] = [];
    const later = (ms: number, fn: () => void) => timers.push(setTimeout(() => !cancelled && fn(), ms));

    setStep({ kind: "typing", chars: 0 });
    let t = 400;
    for (let c = 1; c <= SOURCE.length; c++) {
      // Pausa un poco más en los saltos de línea: se lee como escritura real.
      t += SOURCE[c - 1] === "\n" ? TYPE_SPEED_MS * 5 : TYPE_SPEED_MS;
      later(t, () => setStep({ kind: "typing", chars: c }));
    }
    for (let s = 0; s <= STAGES.length; s++) {
      later(t + 300 + s * STAGE_MS, () => setStep({ kind: "stages", done: s }));
    }
    later(t + 300 + (STAGES.length + 1) * STAGE_MS, () => setStep({ kind: "output" }));

    return () => {
      cancelled = true;
      timers.forEach(clearTimeout);
    };
  }, [reduceMotion, run]);

  const typed = step.kind === "typing" ? SOURCE.slice(0, step.chars) : SOURCE;
  const stagesDone = step.kind === "typing" ? -1 : step.kind === "stages" ? step.done : STAGES.length;
  const showOutput = step.kind === "output";

  return (
    <Frame label="app.dscops" className="overflow-hidden">
      {/* Código fuente */}
      <div className="h-[310px] overflow-hidden px-4 pb-3 pt-5">
        <Code source={typed} language="dscops" caret={step.kind === "typing"} />
      </div>

      {/* Fases del compilador */}
      <ol className="grid grid-cols-4 border-y border-line-soft" aria-label="Fases del compilador">
        {STAGES.map((name, i) => {
          const done = i < stagesDone;
          const active = i === stagesDone && step.kind === "stages";
          return (
            <li
              key={name}
              className="relative flex items-center gap-2 border-r border-line-soft px-3 py-2.5 text-xs last:border-r-0"
            >
              <motion.span
                className="grid size-4 shrink-0 place-items-center rounded-full border"
                animate={{
                  borderColor: done ? "#5fd3a0" : active ? "#f2b33d" : "#1f4470",
                  backgroundColor: done ? "rgba(95,211,160,0.15)" : "rgba(0,0,0,0)",
                }}
                transition={{ duration: 0.25 }}
              >
                {done && <IconCheck size={10} className="text-pass" strokeWidth={3} />}
              </motion.span>
              <span className={done ? "text-paper" : "text-pencil"}>{name}</span>
              {active && (
                <motion.span
                  layoutId="demo-stage"
                  className="absolute inset-x-0 bottom-0 h-0.5 bg-amber"
                  transition={{ type: "spring", stiffness: 500, damping: 40 }}
                />
              )}
            </li>
          );
        })}
      </ol>

      {/* Resultado */}
      <div className="relative h-[250px] overflow-hidden">
        <AnimatePresence mode="wait">
          {showOutput ? (
            <motion.div
              key="output"
              initial={{ opacity: 0, y: 12 }}
              animate={{ opacity: 1, y: 0 }}
              exit={{ opacity: 0 }}
              transition={{ duration: 0.35, ease: "easeOut" }}
              className="flex h-full flex-col"
            >
              <div className="flex items-center justify-between gap-3 border-b border-line-soft px-4 py-2 text-xs">
                <span className="flex items-center gap-1.5 text-sky">
                  <IconInfo size={13} /> SEC007: a «api» le faltan límites de CPU y memoria
                </span>
                <button
                  type="button"
                  onClick={() => setRun((r) => r + 1)}
                  className="flex items-center gap-1 text-pencil transition-colors hover:text-paper"
                >
                  <IconRefresh size={12} /> Repetir
                </button>
              </div>
              <div className="relative flex-1 overflow-hidden px-4 py-3">
                <span className="absolute right-4 top-3 font-mono text-[11px] text-pencil">compose.yaml (extracto)</span>
                <Code source={OUTPUT} language="yaml" showLineNumbers={false} />
                <div className="pointer-events-none absolute inset-x-0 bottom-0 h-16 bg-gradient-to-t from-ink-deep to-transparent" />
              </div>
            </motion.div>
          ) : (
            <motion.p
              key="waiting"
              initial={{ opacity: 0 }}
              animate={{ opacity: 1 }}
              exit={{ opacity: 0 }}
              className="grid h-full place-items-center font-mono text-xs text-pencil/70"
            >
              {step.kind === "typing" ? "escribiendo…" : "compilando…"}
            </motion.p>
          )}
        </AnimatePresence>
      </div>
    </Frame>
  );
}
