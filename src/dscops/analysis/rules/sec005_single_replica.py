"""SEC005: public services running a single replica."""

from __future__ import annotations

from dscops.domain.diagnostics import Diagnostic, Severity
from dscops.domain.model import InfraModel


class SingleReplicaRule:
    code = "SEC005"

    def check(self, model: InfraModel) -> list[Diagnostic]:
        diagnostics: list[Diagnostic] = []
        for service in model.services:
            if service.public and service.replicas == 1:
                diagnostics.append(
                    Diagnostic(
                        code=self.code,
                        severity=Severity.INFO,
                        message=(
                            f"el servicio público '{service.name}' tiene una sola réplica "
                            "(sin alta disponibilidad)"
                        ),
                        line=service.line,
                        column=service.column,
                        hint="considera replicas: 2 o más para tolerar fallos",
                    )
                )
        return diagnostics
