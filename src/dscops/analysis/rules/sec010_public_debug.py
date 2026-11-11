"""SEC010: debug mode enabled on a public service."""

from __future__ import annotations

from dscops.domain.diagnostics import Diagnostic, Severity
from dscops.domain.model import InfraModel


class PublicDebugRule:
    code = "SEC010"

    def check(self, model: InfraModel) -> list[Diagnostic]:
        diagnostics: list[Diagnostic] = []
        for service in model.services:
            if not service.public:
                continue
            debug = service.env.get("DEBUG")
            if debug is None or debug.secret:
                continue
            if debug.value.strip().lower() not in {"true", "1", "yes", "on"}:
                continue
            diagnostics.append(
                Diagnostic(
                    code=self.code,
                    severity=Severity.WARNING,
                    message=f"el servicio público '{service.name}' tiene DEBUG activado",
                    line=debug.line or service.line,
                    column=debug.column,
                    length=debug.length,
                    hint="desactiva DEBUG en producción: DEBUG: false",
                )
            )
        return diagnostics
