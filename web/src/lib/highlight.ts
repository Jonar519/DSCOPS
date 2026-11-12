/**
 * Resaltado de sintaxis mínimo, sin librerías.
 *
 * Cada función recibe el texto y devuelve una lista de líneas; cada línea es
 * una lista de tokens { type, text }. El componente <Code> pinta cada tipo con
 * un color distinto (ver TOKEN_CLASS).
 */

export type TokenType =
  | "plain"
  | "keyword" // service, database, resource…
  | "entity" // nombre declarado: api, main
  | "property" // image:, port:
  | "string"
  | "number" // números, true, false, null
  | "func" // secret(
  | "operator" // ->  =  ---
  | "punct" // { } ( ) , :
  | "comment";

export interface Token {
  type: TokenType;
  text: string;
}

export type Language = "dscops" | "yaml" | "hcl" | "plain";

export const TOKEN_CLASS: Record<TokenType, string> = {
  plain: "text-paper/90",
  keyword: "text-amber font-medium",
  entity: "text-paper font-semibold",
  property: "text-sky",
  string: "text-code-string",
  number: "text-code-number",
  func: "text-code-func",
  operator: "text-amber",
  punct: "text-pencil/70",
  comment: "text-pencil/80 italic",
};

export function languageFor(path: string): Language {
  if (/\.ya?ml$/i.test(path)) return "yaml";
  if (/\.tf$/i.test(path)) return "hcl";
  if (/\.dscops$/i.test(path)) return "dscops";
  return "plain";
}

export function highlight(source: string, language: Language): Token[][] {
  const lines = source.split("\n");
  switch (language) {
    case "dscops":
      return lines.map(highlightDscopsLine);
    case "yaml":
      return lines.map(highlightYamlLine);
    case "hcl":
      return lines.map(highlightHclLine);
    default:
      return lines.map((text) => [{ type: "plain", text }]);
  }
}

/* ---------------------------------------------------------------- DSCOPS */

const DSCOPS_KEYWORDS = new Set(["service", "database"]);
const LITERALS = new Set(["true", "false", "null"]);

function highlightDscopsLine(line: string): Token[] {
  const tokens: Token[] = [];
  let i = 0;
  let previousWasKeyword = false;

  while (i < line.length) {
    const rest = line.slice(i);
    let m: RegExpMatchArray | null;

    if ((m = rest.match(/^#.*/))) {
      tokens.push({ type: "comment", text: m[0] });
    } else if ((m = rest.match(/^"(?:[^"\\]|\\.)*"?/))) {
      tokens.push({ type: "string", text: m[0] });
    } else if ((m = rest.match(/^->/))) {
      tokens.push({ type: "operator", text: m[0] });
    } else if ((m = rest.match(/^\d+(?:\.\d+)?/))) {
      tokens.push({ type: "number", text: m[0] });
    } else if ((m = rest.match(/^[A-Za-z_][\w-]*/))) {
      const word = m[0];
      const after = line.slice(i + word.length);
      let type: TokenType = "plain";
      if (DSCOPS_KEYWORDS.has(word)) type = "keyword";
      else if (previousWasKeyword) type = "entity";
      else if (LITERALS.has(word)) type = "number";
      else if (/^\s*\(/.test(after)) type = "func";
      else if (/^\s*:/.test(after)) type = "property";
      else if (/^\s*->/.test(after) || /->\s*$/.test(line.slice(0, i))) type = "entity";
      tokens.push({ type, text: word });
      previousWasKeyword = type === "keyword";
      i += word.length;
      continue;
    } else if ((m = rest.match(/^\s+/))) {
      tokens.push({ type: "plain", text: m[0] });
      i += m[0].length;
      continue; // los espacios no reinician previousWasKeyword
    } else {
      tokens.push({ type: /[{}(),:]/.test(rest[0]) ? "punct" : "plain", text: rest[0] });
      i += 1;
      previousWasKeyword = false;
      continue;
    }
    i += m[0].length;
    previousWasKeyword = false;
  }
  return tokens;
}

/* ------------------------------------------------------------------ YAML */

function yamlValue(text: string): Token[] {
  if (!text) return [];
  const trimmed = text.trim();
  const lead = text.slice(0, text.length - text.trimStart().length);
  const out: Token[] = lead ? [{ type: "plain", text: lead }] : [];
  let type: TokenType = "plain";
  if (/^(['"]).*\1$/.test(trimmed)) type = "string";
  else if (/^-?\d+(\.\d+)?$/.test(trimmed) || LITERALS.has(trimmed)) type = "number";
  else if (trimmed.startsWith("#")) type = "comment";
  out.push({ type, text: text.slice(lead.length) });
  return out;
}

function highlightYamlLine(line: string): Token[] {
  if (/^\s*#/.test(line)) return [{ type: "comment", text: line }];
  if (/^---\s*$/.test(line)) return [{ type: "operator", text: line }];

  const m = line.match(/^(\s*)(-\s+)?([\w.\-/"']+)(:)(?=\s|$)(.*)$/);
  if (m) {
    const [, indent, dash = "", key, colon, rest] = m;
    return [
      { type: "plain", text: indent },
      ...(dash ? [{ type: "operator" as const, text: dash }] : []),
      { type: "property", text: key },
      { type: "punct", text: colon },
      ...yamlValue(rest),
    ];
  }
  const item = line.match(/^(\s*)(-\s+)(.*)$/);
  if (item) {
    return [
      { type: "plain", text: item[1] },
      { type: "operator", text: item[2] },
      ...yamlValue(item[3]),
    ];
  }
  return [{ type: "plain", text: line }];
}

/* ------------------------------------------------------------------- HCL */

const HCL_KEYWORDS = new Set([
  "resource", "provider", "variable", "output", "terraform", "locals", "module", "data",
]);

function highlightHclLine(line: string): Token[] {
  const tokens: Token[] = [];
  let i = 0;
  while (i < line.length) {
    const rest = line.slice(i);
    let m: RegExpMatchArray | null;
    if ((m = rest.match(/^(#|\/\/).*/))) {
      tokens.push({ type: "comment", text: m[0] });
    } else if ((m = rest.match(/^"(?:[^"\\]|\\.)*"?/))) {
      tokens.push({ type: "string", text: m[0] });
    } else if ((m = rest.match(/^\d+(?:\.\d+)?/))) {
      tokens.push({ type: "number", text: m[0] });
    } else if ((m = rest.match(/^[A-Za-z_][\w-]*/))) {
      const word = m[0];
      const after = line.slice(i + word.length);
      let type: TokenType = "plain";
      if (HCL_KEYWORDS.has(word) && tokens.every((t) => t.type === "plain" && !t.text.trim())) type = "keyword";
      else if (LITERALS.has(word)) type = "number";
      else if (/^\s*\(/.test(after)) type = "func";
      else if (/^\s*=(?!=)/.test(after)) type = "property";
      tokens.push({ type, text: word });
    } else if ((m = rest.match(/^\s+/))) {
      tokens.push({ type: "plain", text: m[0] });
    } else {
      const ch = rest[0];
      tokens.push({ type: ch === "=" ? "operator" : /[{}()[\],]/.test(ch) ? "punct" : "plain", text: ch });
      i += 1;
      continue;
    }
    i += m[0].length;
  }
  return tokens;
}
