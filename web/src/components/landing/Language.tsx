import { Code } from "../ui/Code";
import { Section } from "./Section";

const CONSTRUCTS = [
  {
    name: "service",
    text: "Un contenedor: imagen, puerto, réplicas, variables de entorno, usuario y límites.",
    code: `service api {
  image: "python:3.12-slim"
  port: 8000
  replicas: 3
  env: { DB_URL: secret("db_url") }
  expose: public
}`,
  },
  {
    name: "database",
    text: "Un motor de datos. DSCOPS elige la imagen, el puerto, el volumen y el healthcheck.",
    code: `database main {
  engine: postgres
  version: "16"
  size: "20GB"
  expose: private
}`,
  },
  {
    name: "->",
    text: "Una dependencia. Se traduce a depends_on en Compose y en Terraform.",
    code: `api -> main
worker -> main`,
  },
];

export function Language() {
  return (
    <Section
      id="lenguaje"
      title="Tres construcciones, nada más"
      intro={
        <>
          El lenguaje describe, no programa: no hay bucles, condicionales ni aritmética. Los secretos se escriben como{" "}
          <code className="font-mono text-code-func">secret(&quot;nombre&quot;)</code> y el compilador nunca conoce su valor.
        </>
      }
    >
      <div className="grid gap-6 md:grid-cols-3">
        {CONSTRUCTS.map((c) => (
          <article key={c.name} className="flex flex-col rounded-lg border border-line bg-ink-deep/70">
            <div className="border-b border-line-soft p-5">
              <h3 className="font-mono text-lg text-amber">{c.name}</h3>
              <p className="mt-2 text-[15px] leading-relaxed text-pencil">{c.text}</p>
            </div>
            <div className="flex-1 p-5">
              <Code source={c.code} language="dscops" showLineNumbers={false} />
            </div>
          </article>
        ))}
      </div>
    </Section>
  );
}
