import { GITHUB_URL } from "@/lib/catalog";

export function Footer() {
  return (
    <footer className="border-t border-line-soft">
      <div className="mx-auto flex max-w-6xl flex-col gap-3 px-5 py-8 text-sm text-pencil sm:flex-row sm:items-center sm:justify-between">
        <p>DSCOPS, compilador declarativo con análisis DevSecOps. Licencia MIT.</p>
        <div className="flex gap-5">
          <a href="/docs" className="hover:text-paper">Documentación de la API</a>
          <a href={GITHUB_URL} target="_blank" rel="noreferrer" className="hover:text-paper">
            Código fuente
          </a>
        </div>
      </div>
    </footer>
  );
}
