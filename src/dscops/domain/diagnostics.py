"""DSCOPS domain: diagnostics.

This module is the heart of the compiler contract. It must not import any
third-party library or any other DSCOPS module.
"""

from __future__ import annotations

from dataclasses import dataclass
from enum import StrEnum


class Severity(StrEnum):
    """Severity of a compiler diagnostic."""

    ERROR = "error"
    WARNING = "warning"
    INFO = "info"


@dataclass(frozen=True, slots=True)
class Diagnostic:
    """A structured finding produced by any compiler stage.

    ``column`` and ``length`` are 1-based and refer to the source line. They are
    optional because some findings (for example a missing property) point at a
    whole declaration instead of a token.
    """

    code: str
    severity: Severity
    message: str
    line: int | None = None
    column: int | None = None
    hint: str | None = None
    length: int | None = None

    def is_error(self) -> bool:
        return self.severity is Severity.ERROR


def has_errors(diagnostics: tuple[Diagnostic, ...] | list[Diagnostic]) -> bool:
    """Return ``True`` when at least one diagnostic is an error."""

    return any(diagnostic.severity is Severity.ERROR for diagnostic in diagnostics)


def count_by_severity(
    diagnostics: tuple[Diagnostic, ...] | list[Diagnostic],
) -> dict[Severity, int]:
    """Count diagnostics per severity, keeping a stable order."""

    counts = dict.fromkeys(Severity, 0)
    for diagnostic in diagnostics:
        counts[diagnostic.severity] += 1
    return counts


def format_location(diagnostic: Diagnostic, filename: str) -> str:
    """Render ``file:line:column`` for interfaces that need a one-line location."""

    if diagnostic.line is None:
        return filename
    if diagnostic.column is None:
        return f"{filename}:{diagnostic.line}"
    return f"{filename}:{diagnostic.line}:{diagnostic.column}"
