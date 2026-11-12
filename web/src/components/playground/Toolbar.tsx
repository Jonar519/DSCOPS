"use client";

/** Controles pequeños del playground: ejemplos, destinos y estado de la API. */
import { motion } from "motion/react";
import { TARGET_INFO } from "@/lib/catalog";
import { SAMPLES } from "@/lib/samples";
import type { Health, Target } from "@/lib/types";
import { IconCheck, IconChevron } from "../ui/Icons";

export function SamplePicker({ value, onChange }: { value: string; onChange: (id: string) => void }) {
  return (
    <label className="relative inline-flex items-center">
      <span className="sr-only">Cargar un ejemplo</span>
      <select
        value={value}
        onChange={(e) => onChange(e.target.value)}
        className="appearance-none rounded-md border border-line bg-ink pl-3 pr-8 py-1.5 text-xs text-paper transition-colors hover:border-pencil"
      >
        {SAMPLES.map((s) => (
          <option key={s.id} value={s.id}>
            Ejemplo: {s.label}
          </option>
        ))}
      </select>
      <IconChevron size={13} className="pointer-events-none absolute right-2.5 text-pencil" />
    </label>
  );
}

export function TargetPicker({
  targets,
  selected,
  onToggle,
}: {
  targets: Target[];
  selected: string[];
  onToggle: (name: string) => void;
}) {
  return (
    <fieldset className="flex flex-wrap items-center gap-2">
      <legend className="sr-only">Destinos de compilación</legend>
      {targets.map((t) => {
        const on = selected.includes(t.name);
        const info = TARGET_INFO[t.name];
        return (
          <motion.button
            key={t.name}
            type="button"
            role="checkbox"
            aria-checked={on}
            onClick={() => onToggle(t.name)}
            whileTap={{ scale: 0.95 }}
            title={`${t.description}${t.aliases.length ? ` (alias: ${t.aliases.join(", ")})` : ""}`}
            className={`inline-flex items-center gap-1.5 rounded-md border px-2.5 py-1.5 text-xs transition-colors ${
              on ? "border-amber/60 bg-amber/10 text-paper" : "border-line text-pencil hover:border-pencil hover:text-paper"
            }`}
          >
            <span
              className={`grid size-3.5 place-items-center rounded-sm border transition-colors ${
                on ? "border-amber bg-amber text-ink-deep" : "border-pencil/50"
              }`}
            >
              {on && <IconCheck size={10} strokeWidth={3.5} />}
            </span>
            {info?.label ?? t.name}
          </motion.button>
        );
      })}
    </fieldset>
  );
}

export function ApiStatus({ health }: { health: Health | null | "offline" }) {
  const offline = health === "offline";
  const label = health === null ? "Conectando con la API…" : offline ? "API sin conexión" : `API v${health.version}`;
  return (
    <span className="inline-flex items-center gap-2 text-xs text-pencil" role="status">
      <span className="relative flex size-2">
        {!offline && health !== null && (
          <span className="absolute inline-flex size-full animate-ping rounded-full bg-pass opacity-60" />
        )}
        <span
          className={`relative inline-flex size-2 rounded-full ${
            health === null ? "bg-pencil" : offline ? "bg-fail" : "bg-pass"
          }`}
        />
      </span>
      {label}
    </span>
  );
}
