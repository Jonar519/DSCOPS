"""SEC001: hardcoded secrets in environment variables."""

from __future__ import annotations

from dscops.domain.diagnostics import Diagnostic, Severity
from dscops.domain.model import InfraModel
from dscops.shared.values import is_sensitive_env_key


class HardcodedSecretRule:
    code = "SEC001"

    def check(self, model: InfraModel) -> list[Diagnostic]:
        diagnostics: list[Diagnostic] = []
        for service in model.services:
            for key, env_value in service.env.items():
                if env_value.secret or not is_sensitive_env_key(key):
                    continue
                diagnostics.append(
                    Diagnostic(
                        code=self.code,
                        severity=Severity.ERROR,
                        message=f"secreto hardcodeado en '{key}' del servicio '{service.name}'",
                        line=env_value.line or service.line,
                        column=env_value.column,
                        length=env_value.length,
                        hint=f'usa {key}: secret("{key.lower()}") en lugar de un valor literal',
                    )
                )
        return diagnostics
