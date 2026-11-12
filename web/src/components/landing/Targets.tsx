import { TARGET_INFO } from "@/lib/catalog";
import { LinkButton } from "../ui/Button";
import { IconFile, IconPlay } from "../ui/Icons";
import { Section } from "./Section";

const DETAILS: Record<string, string> = {
  compose: "Servicios, volúmenes, healthchecks y depends_on. Usuario no root por defecto.",
  kubernetes: "Deployment, Service, Ingress, StatefulSet y PVC en un solo archivo multi-documento.",
  "github-actions": "Un workflow que valida y compila en cada push y pull request, y sube los archivos generados.",
  terraform: "Red, imágenes y contenedores con el provider kreuzwerker/docker. Los secretos son variables sensibles.",
};

export function Targets() {
  return (
    <Section
      id="destinos"
      title="Un archivo, cuatro destinos"
      intro="El mismo modelo produce siempre el mismo texto, así los archivos generados se pueden revisar en un pull request."
    >
      <ul className="grid gap-px overflow-hidden rounded-lg border border-line bg-line sm:grid-cols-2">
        {Object.entries(TARGET_INFO).map(([name, info]) => (
          <li key={name} className="bg-ink-deep p-6">
            <div className="flex items-baseline justify-between gap-4">
              <h3 className="text-lg font-semibold">{info.label}</h3>
              <span className="font-mono text-xs text-pencil">--target {name}</span>
            </div>
            <p className="mt-2 text-[15px] leading-relaxed text-pencil">{DETAILS[name]}</p>
            <p className="mt-4 inline-flex items-center gap-1.5 font-mono text-[13px] text-code-string">
              <IconFile size={13} /> {info.file}
            </p>
          </li>
        ))}
      </ul>

      <div className="mt-16 flex flex-col items-start justify-between gap-6 rounded-lg border border-amber/30 bg-amber/[0.06] p-8 sm:flex-row sm:items-center">
        <div>
          <h3 className="text-2xl font-semibold tracking-tight">Pruébalo con tu propia infraestructura</h3>
          <p className="mt-2 text-pencil">El playground usa la misma API que el CLI. No guarda nada.</p>
        </div>
        <LinkButton href="/playground" variant="primary" className="shrink-0 px-5 py-2.5">
          <IconPlay size={14} /> Abrir el playground
        </LinkButton>
      </div>
    </Section>
  );
}
