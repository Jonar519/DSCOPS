"use client";

import { motion } from "motion/react";
import { Section } from "./Section";

/** Las fases reales del compilador, en orden (ver docs/architecture.md). */
const STAGES = [
  {
    name: "Frontend",
    folder: "frontend/",
    input: ".dscops",
    output: "AST",
    text: "Lark con un parser LALR lee el archivo y construye el árbol sintáctico. Los errores llevan línea, columna y sugerencia.",
  },
  {
    name: "Semántica",
    folder: "semantic/",
    input: "AST",
    output: "IR",
    text: "Tabla de símbolos, tipos y rangos. Detecta propiedades desconocidas, nombres duplicados y enlaces rotos.",
  },
  {
    name: "Seguridad",
    folder: "analysis/",
    input: "IR",
    output: "hallazgos",
    text: "Diez reglas DevSecOps revisan el modelo. Un error detiene la compilación; un aviso solo informa.",
  },
  {
    name: "Backends",
    folder: "backends/",
    input: "IR",
    output: "archivos",
    text: "Cada backend traduce el IR neutral a su formato. No conocen el lenguaje, solo el modelo.",
  },
];

export function Pipeline() {
  return (
    <Section
      id="pipeline"
      title="Cómo funciona por dentro"
      intro="Un compilador clásico en cuatro fases. Cada fase solo conoce el formato de entrada y el de salida, así se pueden probar por separado."
    >
      <ol className="relative grid gap-10 md:grid-cols-4 md:gap-6">
        {/* Línea que une las fases: se dibuja una vez al entrar en pantalla. */}
        <motion.span
          aria-hidden="true"
          className="absolute left-[15px] top-4 hidden h-px origin-left bg-amber/60 md:right-[calc(25%-15px)] md:block"
          initial={{ scaleX: 0 }}
          whileInView={{ scaleX: 1 }}
          viewport={{ once: true, amount: 0.6 }}
          transition={{ duration: 1.1, ease: [0.22, 1, 0.36, 1] }}
        />
        {STAGES.map((stage, i) => (
          <motion.li
            key={stage.name}
            className="relative"
            initial={{ opacity: 0 }}
            whileInView={{ opacity: 1 }}
            viewport={{ once: true, amount: 0.6 }}
            transition={{ duration: 0.4, delay: 0.15 + i * 0.22 }}
          >
            <span className="relative z-10 grid size-8 place-items-center rounded-full border border-amber/70 bg-ink font-mono text-sm text-amber">
              {i + 1}
            </span>
            <h3 className="mt-5 text-xl font-semibold">{stage.name}</h3>
            <p className="mt-1 font-mono text-[13px] text-pencil">
              {stage.input} <span className="text-amber">→</span> {stage.output}
            </p>
            <p className="mt-3 text-[15px] leading-relaxed text-pencil">{stage.text}</p>
            <p className="mt-3 font-mono text-xs text-pencil/60">src/dscops/{stage.folder}</p>
          </motion.li>
        ))}
      </ol>
    </Section>
  );
}
