"""Application pipeline tests."""

from __future__ import annotations

import pytest

from dscops.app import MAX_SOURCE_LENGTH, check_source, compile_source, compiler, targets
from dscops.domain.diagnostics import Severity
from dscops.domain.model import InfraModel


def test_check_valid_source(valid_source: str) -> None:
    result = check_source(valid_source)
    assert result.ok is True
    assert result.diagnostics == ()


def test_check_insecure_source_has_findings(insecure_source: str) -> None:
    result = check_source(insecure_source)
    assert result.ok is False
    codes = {diagnostic.code for diagnostic in result.diagnostics}
    assert {"SEC001", "SEC003", "SEC008"} <= codes
    assert any(diagnostic.severity is Severity.WARNING for diagnostic in result.diagnostics)


def test_check_syntax_error(insecure_source: str) -> None:
    result = check_source("service api {")
    assert result.ok is False
    assert [diagnostic.code for diagnostic in result.diagnostics] == ["SYN001"]


def test_compile_all_targets(valid_source: str) -> None:
    result = compile_source(valid_source, ["compose", "kubernetes", "github", "terraform"])
    assert result.ok is True
    assert result.diagnostics == ()
    assert result.targets == ("compose", "kubernetes", "github-actions", "terraform")
    assert [artifact.path for artifact in result.artifacts] == [
        "compose.yaml",
        "k8s.yaml",
        ".github/workflows/dscops.yml",
        "terraform/main.tf",
    ]


def test_compile_deduplicates_target_aliases(valid_source: str) -> None:
    result = compile_source(valid_source, ["compose", "docker", "k8s"])
    assert result.targets == ("compose", "kubernetes")
    assert len(result.artifacts) == 2


def test_compile_without_targets(valid_source: str) -> None:
    result = compile_source(valid_source, [])
    assert result.ok is False
    assert result.artifacts == ()
    assert any(diagnostic.code == "CFG001" for diagnostic in result.diagnostics)


def test_compile_with_unknown_target(valid_source: str) -> None:
    result = compile_source(valid_source, ["compose", "nope"])
    assert result.ok is False
    assert result.artifacts == ()
    diagnostic = next(item for item in result.diagnostics if item.code == "CFG002")
    assert "nope" in diagnostic.message
    assert diagnostic.hint is not None


def test_compile_does_not_generate_when_source_has_errors(insecure_source: str) -> None:
    result = compile_source(insecure_source, ["compose"])
    assert result.ok is False
    assert result.artifacts == ()
    assert result.targets == ("compose",)


def test_source_size_limit() -> None:
    source = "x" * (MAX_SOURCE_LENGTH + 1)
    result = check_source(source)
    assert result.ok is False
    assert result.diagnostics[0].code == "CFG003"


def test_empty_source_compiles_to_empty_artifacts() -> None:
    result = compile_source("", ["compose"])
    assert result.ok is True
    assert result.artifacts[0].path == "compose.yaml"


def test_backend_failure_is_reported(monkeypatch: pytest.MonkeyPatch, valid_source: str) -> None:
    class BrokenBackend:
        name = "broken"
        description = "broken"

        def generate(self, model: InfraModel) -> list[object]:
            raise RuntimeError("boom")

    monkeypatch.setattr(compiler, "get_backend", lambda _name: BrokenBackend())
    result = compile_source(valid_source, ["compose"])
    assert result.ok is False
    assert result.artifacts == ()
    diagnostic = next(item for item in result.diagnostics if item.code == "GEN001")
    assert "boom" in diagnostic.message


def test_backend_with_no_artifacts_is_reported(
    monkeypatch: pytest.MonkeyPatch, valid_source: str
) -> None:
    class EmptyBackend:
        name = "empty"
        description = "empty"

        def generate(self, model: InfraModel) -> list[object]:
            return []

    monkeypatch.setattr(compiler, "get_backend", lambda _name: EmptyBackend())
    result = compile_source(valid_source, ["compose"])
    assert result.ok is False
    assert result.artifacts == ()
    assert any(diagnostic.code == "GEN002" for diagnostic in result.diagnostics)


def test_available_targets_helper() -> None:
    assert targets() == ("compose", "kubernetes", "github-actions", "terraform")


def test_analysis_stops_after_syntax_error() -> None:
    analysis = compiler.analyze("service")
    assert analysis.model is None
    assert len(analysis.diagnostics) == 1


def test_compile_returns_selected_targets_when_failing(valid_source: str) -> None:
    result = compile_source(valid_source, ["k8s", "unknown"])
    assert result.targets == ("kubernetes",)
    assert result.ok is False


def test_source_is_checked_before_target_resolution(valid_source: str) -> None:
    result = compile_source(valid_source + "\n???", ["unknown"])
    codes = {diagnostic.code for diagnostic in result.diagnostics}
    assert "SYN001" in codes
    assert "CFG002" in codes


def test_check_result_is_stable() -> None:
    first = check_source('service api { image: "x:1" }')
    second = check_source('service api { image: "x:1" }')
    assert first == second


def test_analyze_yields_iterator() -> None:
    analysis = compiler.analyze('service api { image: "x:1" }')
    assert isinstance(analysis.diagnostics, tuple)
    assert isinstance(analysis.model, InfraModel)
