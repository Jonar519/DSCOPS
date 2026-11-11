"""SEC007: missing CPU or memory limits."""

from __future__ import annotations

from dscops.domain.diagnostics import Diagnostic, Severity
from dscops.domain.model import InfraModel


class ResourceLimitsRule:
    code = "SEC007"

    def check(self, model: InfraModel) -> list[Diagnostic]:
        diagnostics: list[Diagnostic] = []
        for service in model.services:
            resources = service.resources
            missing = []
            if resources is None or not resources.cpu:
                missing.append("cpu")
            if resources is None or not resources.memory:
                missing.append("memory")
            if not missing:
                continue
            diagnostics.append(
                Diagnostic(
                    code=self.code,
                    severity=Severity.INFO,
                    message=(
                        f"el servicio '{service.name}' no define límites de {' ni '.join(missing)}"
                    ),
                    line=service.line,
                    column=service.column,
                    hint='agrega resources: { cpu: "500m", memory: "512Mi" }',
                )
            )
        return diagnostics
