"""Application layer: the single pipeline used by CLI and API.

Both interfaces call only these functions. Backends, rules and the parser are
injected through their registries, so this module has no interface-specific
logic.
"""

from __future__ import annotations

import logging
from dataclasses import dataclass, field

from dscops.analysis import run_rules
from dscops.backends import (
    Artifact,
    TargetInfo,
    UnknownTarget,
    available_targets,
    canonical_target,
    get_backend,
)
from dscops.domain.diagnostics import Diagnostic, Severity, has_errors
from dscops.domain.model import InfraModel
from dscops.frontend import ParseError, parse
from dscops.semantic import build_model

logger = logging.getLogger(__name__)

MAX_SOURCE_LENGTH = 100_000


@dataclass(frozen=True, slots=True)
class CheckResult:
    ok: bool
    diagnostics: tuple[Diagnostic, ...] = ()


@dataclass(frozen=True, slots=True)
class CompileResult:
    ok: bool
    diagnostics: tuple[Diagnostic, ...] = ()
    artifacts: tuple[Artifact, ...] = ()
    targets: tuple[str, ...] = ()


@dataclass(frozen=True, slots=True)
class _Analysis:
    model: InfraModel | None
    diagnostics: tuple[Diagnostic, ...] = field(default_factory=tuple)


def _diagnostic(
    code: str,
    message: str,
    *,
    hint: str | None = None,
) -> Diagnostic:
    return Diagnostic(code=code, severity=Severity.ERROR, message=message, hint=hint)


def analyze(source: str) -> _Analysis:
    """Run the frontend, semantics and security analysis.

    Syntax errors stop the pipeline because there is no useful AST. Semantic
    errors do not stop the security rules: showing every actionable finding is
    more useful to the user, and compilation still refuses to generate output.
    """

    if len(source) > MAX_SOURCE_LENGTH:
        return _Analysis(
            model=None,
            diagnostics=(
                _diagnostic(
                    "CFG003",
                    f"el archivo supera el límite de {MAX_SOURCE_LENGTH} caracteres",
                    hint="divide la infraestructura en archivos más pequeños",
                ),
            ),
        )
    try:
        ast = parse(source)
    except ParseError as error:
        return _Analysis(model=None, diagnostics=(error.diagnostic,))

    semantic = build_model(ast)
    findings = list(semantic.diagnostics)
    findings.extend(run_rules(semantic.model))
    return _Analysis(model=semantic.model, diagnostics=tuple(findings))


def check_source(source: str) -> CheckResult:
    """Validate source and return semantic + security diagnostics."""

    analysis = analyze(source)
    return CheckResult(
        ok=not has_errors(analysis.diagnostics),
        diagnostics=analysis.diagnostics,
    )


def compile_source(source: str, targets: list[str]) -> CompileResult:
    """Compile ``source`` for every requested target.

    Generation is atomic: if any diagnostic is an error, no artifacts are
    returned. Unknown targets are user errors, not server errors.
    """

    analysis = analyze(source)
    diagnostics = list(analysis.diagnostics)

    if not targets:
        diagnostics.append(
            _diagnostic(
                "CFG001",
                "no se pidió ningún target de compilación",
                hint=f"targets disponibles: {', '.join(target.name for target in available_targets())}",
            )
        )

    selected: list[str] = []
    for requested in targets:
        try:
            canonical = canonical_target(requested)
        except UnknownTarget as error:
            diagnostics.append(
                _diagnostic(
                    "CFG002",
                    f"target desconocido: '{requested}'",
                    hint=f"targets disponibles: {', '.join(error.available)}",
                )
            )
            continue
        if canonical not in selected:
            selected.append(canonical)

    if has_errors(diagnostics) or analysis.model is None:
        return CompileResult(
            ok=False,
            diagnostics=tuple(diagnostics),
            artifacts=(),
            targets=tuple(selected),
        )

    artifacts: list[Artifact] = []
    try:
        for target in selected:
            artifacts.extend(get_backend(target).generate(analysis.model))
    except Exception as error:  # noqa: BLE001 - a backend bug must not crash the API
        logger.exception("falló el backend %s", target)
        diagnostics.append(
            _diagnostic(
                "GEN001",
                f"falló un backend al generar artefactos: {error}",
                hint="revisa el modelo o reporta el error con el archivo .dscops",
            )
        )
        return CompileResult(
            ok=False,
            diagnostics=tuple(diagnostics),
            artifacts=(),
            targets=tuple(selected),
        )

    if not artifacts:
        diagnostics.append(
            _diagnostic(
                "GEN002",
                "no se generó ningún artefacto",
                hint="el archivo no declara servicios ni bases de datos",
            )
        )

    return CompileResult(
        ok=not has_errors(diagnostics),
        diagnostics=tuple(diagnostics),
        artifacts=tuple(artifacts),
        targets=tuple(selected),
    )


def target_infos() -> tuple[TargetInfo, ...]:
    """Backend metadata used by the thin CLI/API interfaces."""

    return available_targets()


def targets() -> tuple[str, ...]:
    return tuple(target.name for target in target_infos())
