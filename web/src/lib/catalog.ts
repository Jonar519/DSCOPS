/**
 * Datos estáticos que se muestran en la página de inicio y en el playground.
 * Fuente: docs/rules.md y src/dscops/backends/.
 */
import type { Severity, Target } from "./types";

export interface Rule {
  code: string;
  severity: Severity;
  title: string;
  detects: string;
  where: "análisis" | "semántica";
}

export const RULES: Rule[] = [
  { code: "SEC001", severity: "error", title: "Secreto hardcodeado", detects: "Una variable sensible (PASSWORD, TOKEN, DB_URL…) con valor literal.", where: "análisis" },
  { code: "SEC002", severity: "warning", title: "Imagen sin versión", detects: "Imágenes sin tag o con :latest.", where: "análisis" },
  { code: "SEC003", severity: "error", title: "Base de datos pública", detects: "Un database con expose: public.", where: "análisis" },
  { code: "SEC004", severity: "warning", title: "Puerto público", detects: "Servicio público sin puerto o con 22, 3306, 5432, 6379, 27017.", where: "análisis" },
  { code: "SEC005", severity: "info", title: "Una sola réplica pública", detects: "Servicio público con replicas: 1.", where: "análisis" },
  { code: "SEC006", severity: "warning", title: "Contenedor root", detects: "Falta user o el usuario es root/0.", where: "análisis" },
  { code: "SEC007", severity: "info", title: "Límites ausentes", detects: "Falta resources, cpu o memory.", where: "análisis" },
  { code: "SEC008", severity: "error", title: "Dependencia inexistente", detects: "origen -> destino con un recurso no declarado.", where: "semántica" },
  { code: "SEC009", severity: "error", title: "Recurso duplicado", detects: "Dos recursos con el mismo nombre.", where: "semántica" },
  { code: "SEC010", severity: "warning", title: "DEBUG público", detects: "DEBUG: true en un servicio público.", where: "análisis" },
];

/** Nombre legible y archivo que genera cada backend. */
export const TARGET_INFO: Record<string, { label: string; file: string }> = {
  compose: { label: "Docker Compose", file: "compose.yaml" },
  kubernetes: { label: "Kubernetes", file: "k8s.yaml" },
  "github-actions": { label: "GitHub Actions", file: ".github/workflows/dscops.yml" },
  terraform: { label: "Terraform", file: "terraform/main.tf" },
};

/** Se usa si la API no responde a /v1/targets. */
export const FALLBACK_TARGETS: Target[] = [
  { name: "compose", description: "Docker Compose (compose.yaml)", aliases: ["docker", "docker-compose"] },
  { name: "kubernetes", description: "Kubernetes manifests", aliases: ["k8s"] },
  { name: "github-actions", description: "GitHub Actions workflow", aliases: ["github", "gha"] },
  { name: "terraform", description: "Terraform (main.tf)", aliases: ["tf"] },
];

export const DEFAULT_TARGETS = ["compose", "kubernetes"];

export const SEVERITY_LABEL: Record<Severity, { one: string; many: string }> = {
  error: { one: "error", many: "errores" },
  warning: { one: "advertencia", many: "advertencias" },
  info: { one: "aviso", many: "avisos" },
};

export function plural(n: number, severity: Severity): string {
  const label = SEVERITY_LABEL[severity];
  return `${n} ${n === 1 ? label.one : label.many}`;
}

export const GITHUB_URL = "https://github.com/Jonar519/DSCOPS";
