import { RULES } from "@/lib/catalog";
import { SeverityBadge } from "../ui/SeverityBadge";
import { Section } from "./Section";

export function Rules() {
  return (
    <Section
      id="reglas"
      title="Diez reglas de seguridad"
      intro="Se ejecutan sobre el modelo intermedio en cada validación. Los errores impiden generar archivos; las advertencias y los avisos no."
    >
      <div className="overflow-x-auto rounded-lg border border-line bg-ink-deep/70">
        <table className="w-full min-w-[640px] text-left text-[15px]">
          <thead className="border-b border-line text-sm text-pencil">
            <tr>
              <th className="px-5 py-3 font-medium">Código</th>
              <th className="px-5 py-3 font-medium">Severidad</th>
              <th className="px-5 py-3 font-medium">Regla</th>
              <th className="px-5 py-3 font-medium">Qué detecta</th>
            </tr>
          </thead>
          <tbody>
            {RULES.map((rule) => (
              <tr key={rule.code} className="border-b border-line-soft transition-colors last:border-0 hover:bg-ink-soft/60">
                <td className="px-5 py-3.5 font-mono text-sm text-paper">{rule.code}</td>
                <td className="px-5 py-3.5"><SeverityBadge severity={rule.severity} /></td>
                <td className="px-5 py-3.5 font-medium">{rule.title}</td>
                <td className="px-5 py-3.5 text-pencil">{rule.detects}</td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
      <p className="mt-4 text-sm text-pencil">
        SEC008 y SEC009 se detectan en la fase semántica porque necesitan la tabla de símbolos.
      </p>
    </Section>
  );
}
