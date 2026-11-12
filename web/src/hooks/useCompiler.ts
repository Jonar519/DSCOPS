"use client";

/**
 * Todo el estado del playground vive aquí. Los componentes solo pintan.
 *
 *   source ──(escribir)──► validación automática tras 600 ms
 *          ──(Compilar)──► diagnósticos + artefactos
 */
import { useCallback, useEffect, useMemo, useRef, useState } from "react";
import { api } from "@/lib/api";
import { DEFAULT_TARGETS, FALLBACK_TARGETS } from "@/lib/catalog";
import { DEFAULT_SAMPLE, SAMPLES } from "@/lib/samples";
import type { Artifact, Diagnostic, Health, Severity, Target } from "@/lib/types";

export type Phase = "idle" | "checking" | "compiling" | "done" | "failed";
export type Verdict = "ok" | "warnings" | "errors" | null;

const AUTO_CHECK_DELAY_MS = 600;

export function useCompiler() {
  const [source, setSourceState] = useState(DEFAULT_SAMPLE.source);
  const [sampleId, setSampleId] = useState(DEFAULT_SAMPLE.id);

  const [targets, setTargets] = useState<Target[]>(FALLBACK_TARGETS);
  const [selected, setSelected] = useState<string[]>(DEFAULT_TARGETS);

  const [phase, setPhase] = useState<Phase>("idle");
  const [diagnostics, setDiagnostics] = useState<Diagnostic[]>([]);
  const [artifacts, setArtifacts] = useState<Artifact[]>([]);
  const [compiledOk, setCompiledOk] = useState<boolean | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [hasResult, setHasResult] = useState(false);
  const [health, setHealth] = useState<Health | null | "offline">(null);

  const offlineRef = useRef(false);
  useEffect(() => {
    offlineRef.current = health === "offline";
  }, [health]);

  // Cada petición recibe un número. Si llega una respuesta vieja, se ignora.
  const requestId = useRef(0);

  /* ---------- Carga inicial: estado de la API y lista de targets ---------- */
  useEffect(() => {
    api.health().then(setHealth).catch(() => setHealth("offline"));
    api.targets().then(setTargets).catch(() => undefined);
  }, []);

  /* --------------------------------- Acciones -------------------------------- */
  const check = useCallback(async (code: string) => {
    const id = ++requestId.current;
    setPhase("checking");
    setError(null);
    try {
      const result = await api.check(code);
      if (id !== requestId.current) return;
      setDiagnostics(result.diagnostics);
      setHasResult(true);
      setPhase("done");
      // Si la API estaba caída y ahora respondió, actualizamos su estado.
      if (offlineRef.current) api.health().then(setHealth).catch(() => undefined);
    } catch (e) {
      if (id !== requestId.current) return;
      setError((e as Error).message);
      setPhase("failed");
    }
  }, []);

  const compile = useCallback(async () => {
    if (!selected.length) {
      setError("Elige al menos un destino para compilar.");
      return;
    }
    const id = ++requestId.current;
    setPhase("compiling");
    setError(null);
    try {
      const result = await api.compile(source, selected);
      if (id !== requestId.current) return;
      setDiagnostics(result.diagnostics);
      setArtifacts(result.artifacts);
      setCompiledOk(result.ok);
      setHasResult(true);
      setPhase("done");
    } catch (e) {
      if (id !== requestId.current) return;
      setError((e as Error).message);
      setArtifacts([]);
      setPhase("failed");
    }
  }, [selected, source]);

  /** Cambiar el código invalida los artefactos y programa una validación. */
  const setSource = useCallback((value: string) => {
    setSourceState(value);
    setArtifacts([]);
    setCompiledOk(null);
  }, []);

  const loadSample = useCallback(
    (id: string) => {
      const sample = SAMPLES.find((s) => s.id === id) ?? DEFAULT_SAMPLE;
      setSampleId(sample.id);
      setSource(sample.source);
    },
    [setSource],
  );

  const toggleTarget = useCallback((name: string) => {
    setSelected((list) => (list.includes(name) ? list.filter((t) => t !== name) : [...list, name]));
  }, []);

  /* ------------------------ Validación automática ------------------------ */
  useEffect(() => {
    const timer = setTimeout(() => void check(source), AUTO_CHECK_DELAY_MS);
    return () => clearTimeout(timer);
  }, [source, check]);

  /* ------------------------------ Derivados ------------------------------ */
  const counts = useMemo(() => {
    const total: Record<Severity, number> = { error: 0, warning: 0, info: 0 };
    for (const d of diagnostics) total[d.severity] += 1;
    return total;
  }, [diagnostics]);

  const verdict: Verdict =
    phase === "idle" || phase === "failed"
      ? null
      : counts.error
        ? "errors"
        : counts.warning || counts.info
          ? "warnings"
          : "ok";

  return {
    // estado
    source, sampleId, targets, selected, phase, diagnostics, artifacts,
    compiledOk, error, health, counts, verdict, hasResult,
    busy: phase === "checking" || phase === "compiling",
    // acciones
    setSource, loadSample, toggleTarget, compile,
    check: () => check(source),
    dismissError: () => setError(null),
  };
}

export type Compiler = ReturnType<typeof useCompiler>;
