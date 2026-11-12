import { GITHUB_URL } from "@/lib/catalog";
import { LinkButton } from "../ui/Button";
import { IconGithub } from "../ui/Icons";
import { Logo } from "../ui/Logo";

const LINKS = [
  { href: "/#lenguaje", label: "Lenguaje" },
  { href: "/#pipeline", label: "Cómo funciona" },
  { href: "/#reglas", label: "Reglas" },
  { href: "/docs", label: "API" },
];

export function Nav() {
  return (
    <header className="sticky top-0 z-40 border-b border-line-soft bg-ink/80 backdrop-blur-md">
      <nav className="mx-auto flex h-16 max-w-6xl items-center justify-between gap-6 px-5">
        <Logo />
        <ul className="hidden items-center gap-1 md:flex">
          {LINKS.map((link) => (
            <li key={link.href}>
              <a
                href={link.href}
                className="rounded-md px-3 py-2 text-sm text-pencil transition-colors hover:text-paper"
              >
                {link.label}
              </a>
            </li>
          ))}
        </ul>
        <div className="flex items-center gap-2">
          <a
            href={GITHUB_URL}
            target="_blank"
            rel="noreferrer"
            aria-label="Repositorio en GitHub"
            className="rounded-md p-2 text-pencil transition-colors hover:text-paper"
          >
            <IconGithub size={18} />
          </a>
          <LinkButton href="/playground" variant="primary" className="px-3.5 py-1.5">
            Abrir playground
          </LinkButton>
        </div>
      </nav>
    </header>
  );
}
