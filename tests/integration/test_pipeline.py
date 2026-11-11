"""End-to-end tests across examples, compiler pipeline and serialization."""

from __future__ import annotations

from pathlib import Path

import yaml

from dscops.app import check_source, compile_source
from dscops.backends.compose import ComposeBackend
from dscops.backends.kubernetes import KubernetesBackend
from dscops.domain.model import InfraModel

ROOT = Path(__file__).resolve().parents[2]
EXAMPLES = ROOT / "examples"


def test_shipped_examples_are_valid() -> None:
    for path in sorted(EXAMPLES.glob("*.dscops")):
        result = check_source(path.read_text(encoding="utf-8"))
        assert result.ok is True, (path, result.diagnostics)
        assert result.diagnostics == ()


def test_invalid_examples_are_rejected() -> None:
    insecure = (EXAMPLES / "invalid" / "insecure.dscops").read_text(encoding="utf-8")
    syntax = (EXAMPLES / "invalid" / "syntax-error.dscops").read_text(encoding="utf-8")
    semantic = (EXAMPLES / "invalid" / "semantic-errors.dscops").read_text(encoding="utf-8")

    insecure_result = check_source(insecure)
    assert insecure_result.ok is False
    assert {item.code for item in insecure_result.diagnostics} >= {
        "SEC001",
        "SEC002",
        "SEC003",
        "SEC004",
        "SEC008",
        "SEC010",
    }

    syntax_result = check_source(syntax)
    assert [item.code for item in syntax_result.diagnostics] == ["SYN001"]

    semantic_result = check_source(semantic)
    assert {item.code for item in semantic_result.diagnostics} >= {"SEC008", "SEC009"}


def test_build_all_examples_to_disk(tmp_path: Path) -> None:
    source = (EXAMPLES / "app.dscops").read_text(encoding="utf-8")
    result = compile_source(source, ["compose", "kubernetes", "github", "terraform"])
    assert result.ok is True
    for artifact in result.artifacts:
        destination = tmp_path / artifact.path
        destination.parent.mkdir(parents=True, exist_ok=True)
        destination.write_text(artifact.content, encoding="utf-8")
    assert (tmp_path / "compose.yaml").exists()
    assert (tmp_path / "k8s.yaml").exists()
    assert (tmp_path / "terraform" / "main.tf").exists()
    assert (tmp_path / ".github" / "workflows" / "dscops.yml").exists()

    compose = yaml.safe_load((tmp_path / "compose.yaml").read_text(encoding="utf-8"))
    assert set(compose["services"]) == {"api", "worker", "main", "cache"}
    documents = list(yaml.safe_load_all((tmp_path / "k8s.yaml").read_text(encoding="utf-8")))
    assert {document["kind"] for document in documents if document} == {
        "Deployment",
        "Service",
        "Ingress",
        "StatefulSet",
    }


def test_generation_is_deterministic(model: InfraModel) -> None:
    first = compile_source(
        (EXAMPLES / "app.dscops").read_text(encoding="utf-8"),
        ["compose", "kubernetes"],
    )
    second = compile_source(
        (EXAMPLES / "app.dscops").read_text(encoding="utf-8"),
        ["compose", "kubernetes"],
    )
    assert first.artifacts == second.artifacts


def test_compose_snapshot(model: InfraModel, snapshot: object) -> None:
    content = ComposeBackend().generate(model)[0].content
    assert content == snapshot


def test_kubernetes_snapshot(model: InfraModel, snapshot: object) -> None:
    content = KubernetesBackend().generate(model)[0].content
    assert content == snapshot
