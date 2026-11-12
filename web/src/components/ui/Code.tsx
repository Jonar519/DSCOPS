import { highlight, TOKEN_CLASS, type Language } from "@/lib/highlight";

/** Bloque de código de solo lectura con números de línea y colores. */
export function Code({
  source,
  language,
  showLineNumbers = true,
  caret = false,
  className = "",
}: {
  source: string;
  language: Language;
  showLineNumbers?: boolean;
  /** Muestra un cursor parpadeante al final (para la demo animada). */
  caret?: boolean;
  className?: string;
}) {
  const lines = highlight(caret ? source : source.replace(/\n$/, ""), language);
  const width = String(lines.length).length;

  return (
    <pre className={`font-mono text-[12.5px] leading-[1.7] ${className}`}>
      <code>
        {lines.map((tokens, i) => (
          <div key={i} className="flex">
            {showLineNumbers && (
              <span
                className="mr-4 shrink-0 select-none text-right text-pencil/40"
                style={{ width: `${width}ch` }}
              >
                {i + 1}
              </span>
            )}
            <span className="whitespace-pre">
              {tokens.length === 0 ? " " : tokens.map((t, j) => (
                <span key={j} className={TOKEN_CLASS[t.type]}>{t.text}</span>
              ))}
              {caret && i === lines.length - 1 && (
                <span className="ml-px inline-block h-[1.1em] w-[0.55em] translate-y-[0.2em] animate-blink bg-amber" />
              )}
            </span>
          </div>
        ))}
      </code>
    </pre>
  );
}
