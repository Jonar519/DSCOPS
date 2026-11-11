"""SEC006: containers that run as root (or do not constrain the user)."""

from __future__ import annotations

from dscops.domain.diagnostics import Diagnostic, Severity
from dscops.domain.model import InfraModel


def _is_root(user: str | None) -> bool:
    if user is None:
        return True
    normalized = user.strip().lower()
    if normalized in {"root", "0", "0:0", "root:root"}:
        return True
    return normalized.startswith(("0:", "root:"))


class RootUserRule:
    code = "SEC006"

    def check(self, model: InfraModel) -> list[Diagnostic]:
        diagnostics: list[Diagnostic] = []
        for service in model.services:
            if not _is_root(service.user):
                continue
            detail = "no define 'user'" if service.user is None else f"usa user: {service.user}"
            diagnostics.append(
                Diagnostic(
                    code=self.code,
                    severity=Severity.WARNING,
                    message=f"el contenedor '{service.name}' corre como root: {detail}",
                    line=service.line,
                    column=service.column,
                    hint='declara user: "10001:10001" y crea ese usuario en la imagen',
                )
            )
        return diagnostics
