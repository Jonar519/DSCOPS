"""CLI tests, including exit codes and artifact writing."""

from __future__ import annotations

from pathlib import Path

import pytest
from typer.testing import CliRunner

from dscops.app import CompileResult
from dscops.backends import Artifact
from dscops.interfaces import cli
from dscops.interfaces.cli import _split_targets, app


def test_version(runner: CliRunner) -> None:
    result = runner.invoke(app, ["--version"])
    assert result.exit_code == 0
    assert "dscops 0.1.0" in result.output


def test_check_valid_file(runner: CliRunner, tmp_path: Path, valid_source: str) -> None:
    file = tmp_path / "app.dscops"
    file.write_text(valid_source, encoding="utf-8")
    result = runner.invoke(app, ["check", str(file)])
    assert result.exit_code == 0
    assert "Sin hallazgos" in result.output


def test_check_warnings_do_not_fail_by_default(runner: CliRunner, tmp_path: Path) -> None:
    file = tmp_path / "warn.dscops"
    file.write_text('service api { image: "x:1" }', encoding="utf-8")
    result = runner.invoke(app, ["check", str(file)])
    assert result.exit_code == 0
    assert "SEC006" in result.output


def test_check_strict_fails_on_warnings(runner: CliRunner, tmp_path: Path) -> None:
    file = tmp_path / "warn.dscops"
    file.write_text('service api { image: "x:1" }', encoding="utf-8")
    result = runner.invoke(app, ["check", "--strict", str(file)])
    assert result.exit_code == 1


def test_check_invalid_file(runner: CliRunner, tmp_path: Path, insecure_source: str) -> None:
    file = tmp_path / "bad.dscops"
    file.write_text(insecure_source, encoding="utf-8")
    result = runner.invoke(app, ["check", str(file)])
    assert result.exit_code == 1
    assert "SEC001" in result.output
    assert "Resumen:" in result.output


def test_check_syntax_error(runner: CliRunner, tmp_path: Path) -> None:
    file = tmp_path / "syntax.dscops"
    file.write_text("service api {", encoding="utf-8")
    result = runner.invoke(app, ["check", str(file)])
    assert result.exit_code == 1
    assert "SYN001" in result.output


def test_check_multiple_files(runner: CliRunner, tmp_path: Path, valid_source: str) -> None:
    good = tmp_path / "good.dscops"
    bad = tmp_path / "bad.dscops"
    good.write_text(valid_source, encoding="utf-8")
    bad.write_text('service api { image: "x:1" }', encoding="utf-8")
    result = runner.invoke(app, ["check", str(good), str(bad)])
    assert result.exit_code == 0
    assert "Resumen:" in result.output


def test_check_missing_file(runner: CliRunner, tmp_path: Path) -> None:
    result = runner.invoke(app, ["check", str(tmp_path / "nope.dscops")])
    assert result.exit_code == 1
    assert "no se pudo leer" in result.output


def test_build_writes_artifacts(runner: CliRunner, tmp_path: Path, valid_source: str) -> None:
    file = tmp_path / "app.dscops"
    file.write_text(valid_source, encoding="utf-8")
    out = tmp_path / "dist"
    result = runner.invoke(
        app,
        ["build", str(file), "--target", "compose,k8s", "--out", str(out)],
    )
    assert result.exit_code == 0
    assert (out / "compose.yaml").exists()
    assert (out / "k8s.yaml").exists()
    assert "compose.yaml" in result.output


def test_build_default_targets(runner: CliRunner, tmp_path: Path, valid_source: str) -> None:
    file = tmp_path / "app.dscops"
    file.write_text(valid_source, encoding="utf-8")
    out = tmp_path / "dist"
    result = runner.invoke(app, ["build", str(file), "--out", str(out)])
    assert result.exit_code == 0
    assert (out / "compose.yaml").exists()
    assert (out / "k8s.yaml").exists()


def test_build_all_targets(runner: CliRunner, tmp_path: Path, valid_source: str) -> None:
    file = tmp_path / "app.dscops"
    file.write_text(valid_source, encoding="utf-8")
    out = tmp_path / "dist"
    result = runner.invoke(
        app,
        ["build", str(file), "-t", "github", "-t", "terraform", "--out", str(out)],
    )
    assert result.exit_code == 0
    assert (out / ".github" / "workflows" / "dscops.yml").exists()
    assert (out / "terraform" / "main.tf").exists()


def test_build_unknown_target(runner: CliRunner, tmp_path: Path, valid_source: str) -> None:
    file = tmp_path / "app.dscops"
    file.write_text(valid_source, encoding="utf-8")
    out = tmp_path / "dist"
    result = runner.invoke(app, ["build", str(file), "-t", "nope", "--out", str(out)])
    assert result.exit_code == 1
    assert "CFG002" in result.output
    assert not out.exists()


def test_build_with_errors(runner: CliRunner, tmp_path: Path, insecure_source: str) -> None:
    file = tmp_path / "bad.dscops"
    file.write_text(insecure_source, encoding="utf-8")
    result = runner.invoke(app, ["build", str(file), "--out", str(tmp_path / "dist")])
    assert result.exit_code == 1


def test_build_rejects_unsafe_artifact_path(
    runner: CliRunner,
    tmp_path: Path,
    valid_source: str,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    file = tmp_path / "app.dscops"
    file.write_text(valid_source, encoding="utf-8")
    out = tmp_path / "dist"

    def fake_compile(source: str, targets: list[str]) -> CompileResult:
        return CompileResult(ok=True, artifacts=(Artifact("../escape.txt", "boom"),))

    monkeypatch.setattr(cli, "compile_source", fake_compile)
    result = runner.invoke(app, ["build", str(file), "--out", str(out)])
    assert result.exit_code == 1
    assert "insegura" in result.output
    assert not (tmp_path / "escape.txt").exists()


def test_build_missing_file(runner: CliRunner, tmp_path: Path) -> None:
    result = runner.invoke(app, ["build", str(tmp_path / "nope.dscops")])
    assert result.exit_code == 1


def test_targets_command(runner: CliRunner) -> None:
    result = runner.invoke(app, ["targets"])
    assert result.exit_code == 0
    assert "compose" in result.output
    assert "kubernetes" in result.output
    assert "github-actions" in result.output
    assert "terraform" in result.output


def test_serve_command(
    runner: CliRunner,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    calls: list[dict[str, object]] = []

    def fake_run(app_path: str, **kwargs: object) -> None:
        calls.append({"app": app_path, **kwargs})

    monkeypatch.setattr(cli.uvicorn, "run", fake_run)
    result = runner.invoke(app, ["serve", "--host", "0.0.0.0", "--port", "9000", "--reload"])
    assert result.exit_code == 0
    assert calls == [
        {
            "app": "dscops.interfaces.api.app:app",
            "host": "0.0.0.0",
            "port": 9000,
            "reload": True,
        }
    ]


def test_split_targets() -> None:
    assert _split_targets(["compose,k8s", " terraform "]) == ["compose", "k8s", "terraform"]


def test_cli_without_arguments_shows_help(runner: CliRunner) -> None:
    result = runner.invoke(app, [])
    assert result.exit_code == 0
    assert "Usage" in result.output
