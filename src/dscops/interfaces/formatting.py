"""Human-readable diagnostic rendering for the CLI.

The Rust-like layout is intentionally implemented with ``rich.text.Text``
instead of markup: source code may contain ``[`` and must never be interpreted
as Rich markup.
"""

from __future__ import annotations

from collections.abc import Iterable

from rich.console import Console
from rich.text import Text

from dscops.domain.diagnostics import Diagnostic, Severity, count_by_severity, format_location

_SEVERITY_STYLES = {
    Severity.ERROR: "bold red",
    Severity.WARNING: "bold yellow",
    Severity.INFO: "bold cyan",
}


def print_diagnostics(
    console: Console,
    filename: str,
    source: str,
    diagnostics: Iterable[Diagnostic],
) -> None:
    ordered = sorted(
        diagnostics,
        key=lambda item: (item.line or 0, item.column or 0, item.code),
    )
    for diagnostic in ordered:
        _print_one(console, filename, source, diagnostic)


def _print_one(console: Console, filename: str, source: str, diagnostic: Diagnostic) -> None:
    header = Text()
    header.append(diagnostic.severity.value, style=_SEVERITY_STYLES[diagnostic.severity])
    header.append(f"[{diagnostic.code}]: ", style="bold")
    header.append(diagnostic.message)
    console.print(header)

    if diagnostic.line is None:
        console.print(Text(f"  --> {filename}", style="dim"))
    else:
        location = format_location(diagnostic, filename)
        console.print(Text(f"  --> {location}", style="dim"))
        _print_snippet(console, source, diagnostic)

    if diagnostic.hint:
        hint = Text("   ")
        hint.append("= ayuda: ", style="bold cyan")
        hint.append(diagnostic.hint)
        console.print(hint)
    console.print()


def _print_snippet(console: Console, source: str, diagnostic: Diagnostic) -> None:
    lines = source.splitlines()
    line_number = diagnostic.line
    if line_number is None or line_number < 1 or line_number > len(lines):
        return
    source_line = lines[line_number - 1].expandtabs(4)
    gutter = len(str(line_number))
    console.print(Text(f"{' ' * (gutter + 2)}|", style="dim"))
    line_text = Text()
    line_text.append(f"{line_number:>{gutter}} | ", style="dim")
    line_text.append(source_line)
    console.print(line_text)

    if diagnostic.column is None:
        return
    column = max(1, diagnostic.column)
    length = max(1, diagnostic.length or 1)
    available = max(1, len(source_line) - (column - 1))
    caret = "^" * min(length, available)
    caret_text = Text()
    caret_text.append(f"{' ' * (gutter + 1)}| ", style="dim")
    caret_text.append(" " * (column - 1) + caret, style=_SEVERITY_STYLES[diagnostic.severity])
    console.print(caret_text)


def print_summary(console: Console, diagnostics: Iterable[Diagnostic]) -> None:
    items = tuple(diagnostics)
    if not items:
        console.print(Text("Sin hallazgos.", style="green"))
        return
    counts = count_by_severity(items)
    parts = []
    if counts[Severity.ERROR]:
        parts.append(f"{counts[Severity.ERROR]} error(es)")
    if counts[Severity.WARNING]:
        parts.append(f"{counts[Severity.WARNING]} advertencia(s)")
    if counts[Severity.INFO]:
        parts.append(f"{counts[Severity.INFO]} aviso(s)")
    console.print(Text("Resumen: " + ", ".join(parts), style="bold"))
