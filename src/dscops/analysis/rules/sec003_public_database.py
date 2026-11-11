"""SEC003: a database exposed to the public internet."""

from __future__ import annotations

from dscops.domain.diagnostics import Diagnostic, Severity
from dscops.domain.model import InfraModel


class PublicDatabaseRule:
    code = "SEC003"

    def check(self, model: InfraModel) -> list[Diagnostic]:
        return [
            Diagnostic(
                code=self.code,
                severity=Severity.ERROR,
                message=f"la base de datos '{database.name}' está expuesta públicamente",
                line=database.line,
                column=database.column,
                hint="usa expose: private; las bases de datos no deben ser accesibles desde internet",
            )
            for database in model.databases
            if database.public
        ]
