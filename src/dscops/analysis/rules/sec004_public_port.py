"""SEC004: public services with a missing or sensitive port."""

from __future__ import annotations

from dscops.domain.diagnostics import Diagnostic, Severity
from dscops.domain.model import InfraModel

SENSITIVE_PORTS = {22, 3306, 5432, 6379, 27017}


class PublicPortRule:
    code = "SEC004"

    def check(self, model: InfraModel) -> list[Diagnostic]:
        diagnostics: list[Diagnostic] = []
        for service in model.services:
            if not service.public:
                continue
            if service.port is None:
                diagnostics.append(
                    Diagnostic(
                        code=self.code,
                        severity=Severity.WARNING,
                        message=f"el servicio público '{service.name}' no define un puerto",
                        line=service.line,
                        column=service.column,
                        hint="agrega port: 8000 para que el servicio sea accesible",
                    )
                )
            elif service.port in SENSITIVE_PORTS:
                diagnostics.append(
                    Diagnostic(
                        code=self.code,
                        severity=Severity.WARNING,
                        message=(
                            f"el servicio público '{service.name}' expone el puerto sensible "
                            f"{service.port}"
                        ),
                        line=service.line,
                        column=service.column,
                        hint="publica un puerto no privilegiado y pon un proxy delante",
                    )
                )
        return diagnostics
