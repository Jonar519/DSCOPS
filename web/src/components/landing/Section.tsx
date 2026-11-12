import type { ReactNode } from "react";

/** Envoltorio común de las secciones de la página de inicio. */
export function Section({
  id,
  title,
  intro,
  children,
}: {
  id: string;
  title: string;
  intro?: ReactNode;
  children: ReactNode;
}) {
  return (
    <section id={id} className="scroll-mt-20 border-t border-line-soft">
      <div className="mx-auto max-w-6xl px-5 py-20">
        <div className="mb-12 max-w-2xl">
          <h2 className="text-3xl font-semibold tracking-[-0.02em] sm:text-4xl">{title}</h2>
          {intro && <p className="mt-4 text-lg leading-relaxed text-pencil">{intro}</p>}
        </div>
        {children}
      </div>
    </section>
  );
}
