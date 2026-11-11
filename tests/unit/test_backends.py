"""Backend tests: structure, security defaults and deterministic serialization."""

from __future__ import annotations

import pytest
import yaml

from dscops.backends import (
    UnknownTarget,
    available_targets,
    canonical_target,
    get_backend,
)
from dscops.backends._common import database_password_variable
from dscops.backends.compose import ComposeBackend
from dscops.backends.github_actions import GitHubActionsBackend
from dscops.backends.kubernetes import KubernetesBackend
from dscops.backends.terraform import TerraformBackend
from dscops.domain.model import Database, InfraModel, Resources, Service
from dscops.shared.values import normalize_storage_size


def test_registry_targets_and_aliases() -> None:
    names = [target.name for target in available_targets()]
    assert names == ["compose", "kubernetes", "github-actions", "terraform"]
    assert get_backend("k8s").name == "kubernetes"
    assert get_backend("docker").name == "compose"
    assert canonical_target("tf") == "terraform"
    assert canonical_target("gha") == "github-actions"


def test_registry_unknown_target() -> None:
    with pytest.raises(UnknownTarget) as captured:
        get_backend("nope")
    assert captured.value.name == "nope"
    assert "compose" in captured.value.available


def test_compose_valid_model(model: InfraModel) -> None:
    content = ComposeBackend().generate(model)[0].content
    data = yaml.safe_load(content)
    api = data["services"]["api"]
    assert api["image"] == "python:3.12-slim"
    assert api["user"] == "10001:10001"
    assert api["ports"] == ["8000-8002:8000"]
    assert api["environment"]["DB_URL"] == "${DB_URL}"
    assert api["environment"]["DEBUG"] == "false"
    assert api["deploy"]["replicas"] == 3
    assert api["deploy"]["resources"]["limits"]["cpus"] == "0.5"
    assert api["deploy"]["resources"]["limits"]["memory"] == "512M"
    assert api["depends_on"]["main"]["condition"] == "service_healthy"
    assert api["depends_on"]["cache"]["condition"] == "service_healthy"
    assert api["command"] == ["sh", "-c", "python -m http.server 8000"]
    assert api["security_opt"] == ["no-new-privileges:true"]

    worker = data["services"]["worker"]
    assert "ports" not in worker
    assert "expose" not in worker
    assert worker["depends_on"]["main"]["condition"] == "service_healthy"

    main = data["services"]["main"]
    assert main["image"] == "postgres:16"
    assert main["environment"]["POSTGRES_PASSWORD"] == "${MAIN_PASSWORD}"
    assert main["volumes"] == ["main_data:/var/lib/postgresql/data"]
    assert main["healthcheck"]["test"] == ["CMD-SHELL", "pg_isready -U main -d main"]
    assert data["volumes"]["main_data"]["name"] == "dscops_main_data"

    cache = data["services"]["cache"]
    assert cache["image"] == "redis:7.2"
    assert cache["command"] == ["sh", "-c", 'exec redis-server --requirepass "$$REDIS_PASSWORD"']
    assert cache["environment"]["REDIS_PASSWORD"] == "${CACHE_PASSWORD}"


def test_compose_single_replica_and_private_service() -> None:
    model = InfraModel(
        services=(
            Service(
                name="api",
                image="x:1",
                port=8000,
                replicas=1,
                public=True,
                user="1000",
                resources=Resources(cpu="250m", memory="128Mi"),
            ),
            Service(name="worker", image="x:1", port=9000, user="1000"),
        )
    )
    data = yaml.safe_load(ComposeBackend().generate(model)[0].content)
    assert data["services"]["api"]["ports"] == ["8000:8000"]
    assert data["services"]["worker"]["expose"] == ["9000"]
    assert data["services"]["worker"]["deploy"]["replicas"] == 1
    assert "resources" not in data["services"]["worker"]["deploy"]


def test_compose_public_database() -> None:
    database = Database(name="db", engine="postgres", version="16", public=True, size="1GB")
    data = yaml.safe_load(ComposeBackend().generate(InfraModel(databases=(database,)))[0].content)
    assert data["services"]["db"]["ports"] == ["5432:5432"]
    assert data["services"]["db"]["labels"]["dscops.size"] == "1GB"


def test_compose_service_without_port_or_command() -> None:
    model = InfraModel(services=(Service(name="worker", image="x:1"),))
    data = yaml.safe_load(ComposeBackend().generate(model)[0].content)
    service = data["services"]["worker"]
    assert "ports" not in service
    assert "expose" not in service
    assert "command" not in service


def test_compose_does_not_emit_dependency_on_self() -> None:
    model = InfraModel(
        services=(Service(name="api", image="x:1"),),
        links=(),
    )
    data = yaml.safe_load(ComposeBackend().generate(model)[0].content)
    assert "depends_on" not in data["services"]["api"]


def _documents(model: InfraModel) -> list[dict[str, object]]:
    content = KubernetesBackend().generate(model)[0].content
    return [item for item in yaml.safe_load_all(content) if item is not None]


def test_kubernetes_valid_model(model: InfraModel) -> None:
    documents = _documents(model)
    assert [doc["kind"] for doc in documents] == [
        "Deployment",
        "Service",
        "Ingress",
        "Deployment",
        "StatefulSet",
        "Service",
        "StatefulSet",
        "Service",
    ]
    api = documents[0]
    container = api["spec"]["template"]["spec"]["containers"][0]
    assert api["spec"]["replicas"] == 3
    assert container["image"] == "python:3.12-slim"
    assert container["command"] == ["sh", "-c"]
    assert container["args"] == ["python -m http.server 8000"]
    assert container["env"][0] == {
        "name": "DB_URL",
        "valueFrom": {"secretKeyRef": {"name": "api-secrets", "key": "DB_URL"}},
    }
    assert container["resources"]["limits"] == {"cpu": "500m", "memory": "512Mi"}
    assert api["spec"]["template"]["spec"]["securityContext"]["runAsUser"] == 10001
    assert container["securityContext"]["capabilities"]["drop"] == ["ALL"]

    worker = documents[3]
    assert "ports" not in worker["spec"]["template"]["spec"]["containers"][0]

    main = documents[4]
    database_container = main["spec"]["template"]["spec"]["containers"][0]
    assert (
        main["spec"]["volumeClaimTemplates"][0]["spec"]["resources"]["requests"]["storage"]
        == "20Gi"
    )
    assert database_container["env"][1] == {
        "name": "POSTGRES_PASSWORD",
        "valueFrom": {"secretKeyRef": {"name": "main-secrets", "key": "POSTGRES_PASSWORD"}},
    }
    assert documents[5]["spec"]["type"] == "ClusterIP"


def test_kubernetes_public_database_and_redis_args() -> None:
    database = Database(name="cache", engine="redis", public=True)
    documents = _documents(InfraModel(databases=(database,)))
    statefulset = documents[0]
    container = statefulset["spec"]["template"]["spec"]["containers"][0]
    assert container["args"] == ["--requirepass", "$(REDIS_PASSWORD)"]
    assert documents[1]["spec"]["type"] == "LoadBalancer"


def test_kubernetes_service_without_port_has_no_service_or_ingress() -> None:
    model = InfraModel(services=(Service(name="worker", image="x:1", public=True),))
    documents = _documents(model)
    assert [document["kind"] for document in documents] == ["Deployment"]


def test_kubernetes_non_numeric_user_is_not_forced_to_uid() -> None:
    model = InfraModel(services=(Service(name="api", image="x:1", user="app"),))
    documents = _documents(model)
    security = documents[0]["spec"]["template"]["spec"]["securityContext"]
    assert security == {"runAsNonRoot": True}


def test_kubernetes_root_user_does_not_emit_conflicting_context() -> None:
    model = InfraModel(services=(Service(name="api", image="x:1", user="0:0"),))
    documents = _documents(model)
    security = documents[0]["spec"]["template"]["spec"]["securityContext"]
    assert security == {"runAsNonRoot": False, "runAsUser": 0, "runAsGroup": 0, "fsGroup": 0}


def test_kubernetes_database_storage_uses_k8s_quantity() -> None:
    assert normalize_storage_size("20GB") == "20Gi"


def test_github_actions_workflow(model: InfraModel) -> None:
    content = GitHubActionsBackend().generate(model)[0].content
    data = yaml.safe_load(content)
    assert data["name"] == "DSCOPS security gate"
    assert "pull_request" in data["on"]
    steps = data["jobs"]["verify"]["steps"]
    assert any("dscops check" in step.get("run", "") for step in steps)
    upload = next(step for step in steps if step.get("uses") == "actions/upload-artifact@v4")
    assert upload["with"]["include-hidden-files"] is True


def test_terraform_valid_model(model: InfraModel) -> None:
    content = TerraformBackend().generate(model)[0].content
    assert 'variable "db_url"' in content
    assert 'variable "main_password"' in content
    assert 'variable "cache_password"' in content
    assert 'resource "docker_container" "service_api"' in content
    assert "count    = 3" in content
    assert '"DB_URL=${var.db_url}"' in content
    assert '"DEBUG=false"' in content
    assert "memory     = 512" in content
    assert "depends_on = [docker_container.database_main]" in content
    assert "external = 8000 + count.index" in content
    assert 'command    = ["sh", "-c", "python -m http.server 8000"]' in content
    assert '"--requirepass"' in content
    assert 'container_path = "/var/lib/postgresql/data"' in content
    assert "redis-server" in content


def test_terraform_escapes_hcl_and_omits_empty_sections() -> None:
    model = InfraModel(
        services=(
            Service(
                name="api",
                image="x:1",
                command='echo "hi" ${not_hcl}',
                user="1000",
            ),
        )
    )
    content = TerraformBackend().generate(model)[0].content
    assert 'command    = ["sh", "-c", "echo \\"hi\\" $${not_hcl}"]' in content
    assert "env = [" not in content
    assert "memory" not in content
    assert "variable " not in content


def test_terraform_public_database() -> None:
    database = Database(name="db", engine="postgres", public=True)
    content = TerraformBackend().generate(InfraModel(databases=(database,)))[0].content
    assert "internal = 5432" in content
    assert "external = 5432" in content
    assert database_password_variable(database) == "DB_PASSWORD"


def test_artifacts_paths_are_relative(model: InfraModel) -> None:
    for backend in (
        ComposeBackend(),
        KubernetesBackend(),
        GitHubActionsBackend(),
        TerraformBackend(),
    ):
        artifacts = backend.generate(model)
        assert artifacts
        assert all(not artifact.path.startswith("/") for artifact in artifacts)
        assert all(artifact.content for artifact in artifacts)
