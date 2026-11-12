/**
 * Cliente HTTP de la API de DSCOPS.
 *
 * Todas las rutas empiezan por /api: next.config.ts las reenvía a FastAPI.
 * Por eso aquí nunca aparece "localhost:8000".
 */
import type { CheckResponse, CompileResponse, Health, Target } from "./types";

const BASE = "/api";

async function request<T>(path: string, init?: RequestInit): Promise<T> {
  let response: Response;
  try {
    response = await fetch(BASE + path, {
      ...init,
      headers: { "Content-Type": "application/json", ...init?.headers },
    });
  } catch {
    throw new Error("No hay conexión con la API. Arráncala con «dscops serve».");
  }

  let data: unknown;
  try {
    data = await response.json();
  } catch {
    // Next.js responde 500 sin JSON cuando no puede llegar a FastAPI.
    throw new Error(
      `La API no respondió con JSON (HTTP ${response.status}). Comprueba que «dscops serve» esté corriendo.`,
    );
  }

  if (!response.ok) {
    const detail = (data as { detail?: unknown }).detail;
    const text = typeof detail === "string" ? detail : JSON.stringify(detail);
    throw new Error(`HTTP ${response.status}: ${text}`);
  }
  return data as T;
}

export const api = {
  health: () => request<Health>("/health"),
  targets: () => request<Target[]>("/v1/targets"),
  check: (source: string) =>
    request<CheckResponse>("/v1/check", {
      method: "POST",
      body: JSON.stringify({ source }),
    }),
  compile: (source: string, targets: string[]) =>
    request<CompileResponse>("/v1/compile", {
      method: "POST",
      body: JSON.stringify({ source, targets }),
    }),
};
