"""SEC002: images without a tag, or pinned to ``latest``."""

from __future__ import annotations

from dscops.domain.diagnostics import Diagnostic, Severity
from dscops.domain.model import InfraModel
from dscops.shared.values import image_tag, is_pinned_image


class ImageTagRule:
    code = "SEC002"

    def check(self, model: InfraModel) -> list[Diagnostic]:
        diagnostics: list[Diagnostic] = []
        for service in model.services:
            if is_pinned_image(service.image):
                continue
            tag = image_tag(service.image)
            reason = "usa el tag 'latest'" if tag is not None else "no tiene tag"
            diagnostics.append(
                Diagnostic(
                    code=self.code,
                    severity=Severity.WARNING,
                    message=f"la imagen '{service.image}' {reason}",
                    line=service.line,
                    column=service.column,
                    hint='fija una versión explícita, por ejemplo "python:3.12-slim"',
                )
            )
        return diagnostics
