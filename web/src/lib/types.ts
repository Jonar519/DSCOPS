/**
 * Tipos que devuelve la API de DSCOPS.
 * Son un espejo de src/dscops/interfaces/api/schemas.py.
 */

export type Severity = "error" | "warning" | "info";

export interface Diagnostic {
  code: string; // p. ej. "SEC001", "SYN001", "SEM002"
  severity: Severity;
  message: string;
  line: number | null;
  column: number | null;
  length: number | null;
  hint: string | null;
}

export interface Artifact {
  path: string; // p. ej. "compose.yaml"
  content: string;
}

export interface CheckResponse {
  ok: boolean;
  diagnostics: Diagnostic[];
}

export interface CompileResponse extends CheckResponse {
  artifacts: Artifact[];
  targets: string[];
}

export interface Target {
  name: string;
  description: string;
  aliases: string[];
}

export interface Health {
  status: string;
  version: string;
}
