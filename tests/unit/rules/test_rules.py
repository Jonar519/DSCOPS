"""Security rule tests: two cases (fires / does not fire) per rule."""

from __future__ import annotations

from dscops.analysis import RULES, rule_codes, run_rules
from dscops.analysis.rules.sec001_hardcoded_secret import HardcodedSecretRule
from dscops.analysis.rules.sec002_image_tag import ImageTagRule
from dscops.analysis.rules.sec003_public_database import PublicDatabaseRule
from dscops.analysis.rules.sec004_public_port import PublicPortRule
from dscops.analysis.rules.sec005_single_replica import SingleReplicaRule
from dscops.analysis.rules.sec006_root_user import RootUserRule
from dscops.analysis.rules.sec007_resource_limits import ResourceLimitsRule
from dscops.analysis.rules.sec010_public_debug import PublicDebugRule
from dscops.domain.diagnostics import Severity
from dscops.domain.model import Database, EnvValue, InfraModel, Resources, Service
from dscops.frontend import parse
from dscops.semantic import build_model


def service(**overrides: object) -> Service:
    defaults: dict[str, object] = {
        "name": "api",
        "image": "python:3.12-slim",
        "port": 8000,
        "replicas": 2,
        "public": True,
        "user": "10001:10001",
        "resources": Resources(cpu="500m", memory="512Mi"),
        "line": 1,
        "column": 1,
    }
    defaults.update(overrides)
    return Service(**defaults)  # type: ignore[arg-type]


def test_rule_codes_are_stable() -> None:
    assert rule_codes() == (
        "SEC001",
        "SEC002",
        "SEC003",
        "SEC004",
        "SEC005",
        "SEC006",
        "SEC007",
        "SEC010",
    )
    assert len(RULES) == 8


def test_sec001_hardcoded_secret_fires() -> None:
    model = InfraModel(
        services=(
            service(
                env={
                    "DB_PASSWORD": EnvValue("admin123", line=3, column=10, length=8),
                    "MODE": EnvValue("prod"),
                }
            ),
        )
    )
    diagnostics = HardcodedSecretRule().check(model)
    assert len(diagnostics) == 1
    assert diagnostics[0].code == "SEC001"
    assert diagnostics[0].severity is Severity.ERROR
    assert diagnostics[0].line == 3
    assert diagnostics[0].column == 10


def test_sec001_does_not_fire_for_secret_or_benign_key() -> None:
    model = InfraModel(
        services=(
            service(
                env={
                    "DB_PASSWORD": EnvValue("db_password", secret=True),
                    "MODE": EnvValue("prod"),
                }
            ),
        )
    )
    assert HardcodedSecretRule().check(model) == []


def test_sec002_latest_and_untagged_fire() -> None:
    model = InfraModel(services=(service(image="python:latest"), service(name="b", image="python")))
    diagnostics = ImageTagRule().check(model)
    assert len(diagnostics) == 2
    assert all(item.severity is Severity.WARNING for item in diagnostics)


def test_sec002_pinned_and_digest_do_not_fire() -> None:
    model = InfraModel(
        services=(
            service(image="python:3.12-slim"),
            service(name="b", image="registry.example.com:5000/app@sha256:abc"),
        )
    )
    assert ImageTagRule().check(model) == []


def test_sec003_public_database_fires() -> None:
    model = InfraModel(databases=(Database(name="db", engine="postgres", public=True),))
    diagnostics = PublicDatabaseRule().check(model)
    assert len(diagnostics) == 1
    assert diagnostics[0].code == "SEC003"
    assert diagnostics[0].severity is Severity.ERROR


def test_sec003_private_database_does_not_fire() -> None:
    model = InfraModel(databases=(Database(name="db", engine="postgres"),))
    assert PublicDatabaseRule().check(model) == []


def test_sec004_missing_port_fires() -> None:
    diagnostics = PublicPortRule().check(InfraModel(services=(service(port=None),)))
    assert len(diagnostics) == 1
    assert "no define un puerto" in diagnostics[0].message


def test_sec004_sensitive_port_fires_and_normal_port_does_not() -> None:
    sensitive = PublicPortRule().check(InfraModel(services=(service(port=5432),)))
    assert len(sensitive) == 1
    assert "sensible" in sensitive[0].message
    normal = PublicPortRule().check(InfraModel(services=(service(port=8000),)))
    assert normal == []


def test_sec005_single_public_replica_fires() -> None:
    diagnostics = SingleReplicaRule().check(
        InfraModel(services=(service(replicas=1, public=True),))
    )
    assert len(diagnostics) == 1
    assert diagnostics[0].severity is Severity.INFO


def test_sec005_private_or_replicated_does_not_fire() -> None:
    model = InfraModel(
        services=(
            service(replicas=1, public=False),
            service(name="b", replicas=2, public=True),
        )
    )
    assert SingleReplicaRule().check(model) == []


def test_sec006_missing_or_root_user_fires() -> None:
    model = InfraModel(
        services=(
            service(user=None),
            service(name="b", user="root"),
            service(name="c", user="0:0"),
            service(name="d", user="0:1000"),
        )
    )
    assert len(RootUserRule().check(model)) == 4


def test_sec006_non_root_user_does_not_fire() -> None:
    model = InfraModel(services=(service(user="10001:10001"), service(name="b", user="app")))
    assert RootUserRule().check(model) == []


def test_sec007_missing_limits_fire() -> None:
    model = InfraModel(services=(service(resources=None),))
    diagnostics = ResourceLimitsRule().check(model)
    assert len(diagnostics) == 1
    assert "cpu ni memory" in diagnostics[0].message


def test_sec007_partial_limits_and_complete_limits() -> None:
    partial = ResourceLimitsRule().check(
        InfraModel(services=(service(resources=Resources(cpu="1")),))
    )
    assert len(partial) == 1
    assert "memory" in partial[0].message
    complete = ResourceLimitsRule().check(
        InfraModel(services=(service(resources=Resources(cpu="1", memory="1Gi")),))
    )
    assert complete == []


def test_sec010_public_debug_fires() -> None:
    model = InfraModel(services=(service(env={"DEBUG": EnvValue("true")}),))
    diagnostics = PublicDebugRule().check(model)
    assert len(diagnostics) == 1
    assert diagnostics[0].severity is Severity.WARNING


def test_sec010_private_or_disabled_or_secret_does_not_fire() -> None:
    model = InfraModel(
        services=(
            service(public=False, env={"DEBUG": EnvValue("true")}),
            service(name="b", env={"DEBUG": EnvValue("false")}),
            service(name="c", env={"DEBUG": EnvValue("debug", secret=True)}),
            service(name="d", env={"OTHER": EnvValue("true")}),
        )
    )
    assert PublicDebugRule().check(model) == []


def test_all_rules_run_on_insecure_source(insecure_source: str) -> None:
    model = build_model(parse(insecure_source)).model
    diagnostics = run_rules(model)
    codes = {diagnostic.code for diagnostic in diagnostics}
    assert {
        "SEC001",
        "SEC002",
        "SEC003",
        "SEC004",
        "SEC005",
        "SEC006",
        "SEC007",
        "SEC010",
    } <= codes
