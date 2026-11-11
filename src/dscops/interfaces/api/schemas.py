"""Pydantic schemas for the HTTP boundary.

These types never leak into the compiler core: routes translate them to plain
domain values and back.
"""

from __future__ import annotations

from pydantic import BaseModel, ConfigDict, Field

from dscops.app import MAX_SOURCE_LENGTH
from dscops.domain.diagnostics import Diagnostic
from dscops.domain.diagnostics import Severity as DomainSeverity


class _StrictModel(BaseModel):
    model_config = ConfigDict(extra="forbid")


class SourceRequest(_StrictModel):
    source: str = Field(
        max_length=MAX_SOURCE_LENGTH,
        description="Contenido completo de un archivo .dscops.",
    )


class CompileRequest(SourceRequest):
    targets: list[str] = Field(
        max_length=16,
        description="Backends a generar. Ejemplo: ['compose', 'kubernetes'].",
    )


class DiagnosticModel(_StrictModel):
    code: str
    severity: DomainSeverity
    message: str
    line: int | None = None
    column: int | None = None
    length: int | None = None
    hint: str | None = None

    @classmethod
    def from_domain(cls, diagnostic: Diagnostic) -> DiagnosticModel:
        return cls(
            code=diagnostic.code,
            severity=diagnostic.severity,
            message=diagnostic.message,
            line=diagnostic.line,
            column=diagnostic.column,
            length=diagnostic.length,
            hint=diagnostic.hint,
        )


class CheckResponse(_StrictModel):
    ok: bool
    diagnostics: list[DiagnosticModel]


class ArtifactModel(_StrictModel):
    path: str
    content: str


class CompileResponse(CheckResponse):
    artifacts: list[ArtifactModel]
    targets: list[str]


class TargetModel(_StrictModel):
    name: str
    description: str
    aliases: list[str]


class HealthResponse(_StrictModel):
    status: str
    version: str
