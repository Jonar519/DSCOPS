"""Domain contract tests."""

from __future__ import annotations

from dscops.domain.diagnostics import (
    Diagnostic,
    Severity,
    count_by_severity,
    format_location,
    has_errors,
)
from dscops.domain.model import Database, EnvValue, InfraModel, Link, Resources, Service


def test_severity_is_a_string_enum() -> None:
    assert Severity.ERROR == "error"
    assert Severity.WARNING.value == "warning"
    assert Severity.INFO.value == "info"


def test_diagnostic_defaults_and_helpers() -> None:
    diagnostic = Diagnostic(code="X001", severity=Severity.WARNING, message="hola")
    assert diagnostic.is_error() is False
    assert diagnostic.line is None
    assert has_errors([diagnostic]) is False
    assert count_by_severity([diagnostic]) == {
        Severity.ERROR: 0,
        Severity.WARNING: 1,
        Severity.INFO: 0,
    }


def test_has_errors_and_counts() -> None:
    diagnostics = [
        Diagnostic("E1", Severity.ERROR, "e1"),
        Diagnostic("E2", Severity.ERROR, "e2"),
        Diagnostic("W1", Severity.WARNING, "w1"),
        Diagnostic("I1", Severity.INFO, "i1"),
    ]
    assert has_errors(diagnostics) is True
    assert count_by_severity(diagnostics) == {
        Severity.ERROR: 2,
        Severity.WARNING: 1,
        Severity.INFO: 1,
    }


def test_format_location() -> None:
    assert format_location(Diagnostic("X", Severity.ERROR, "m"), "a.dscops") == "a.dscops"
    assert format_location(Diagnostic("X", Severity.ERROR, "m", line=3), "a.dscops") == "a.dscops:3"
    assert (
        format_location(Diagnostic("X", Severity.ERROR, "m", line=3, column=7), "a.dscops")
        == "a.dscops:3:7"
    )


def test_model_helpers() -> None:
    service = Service(name="api", image="x:1")
    database = Database(name="db", engine="postgres")
    model = InfraModel(
        services=(service,),
        databases=(database,),
        links=(Link(source="api", target="db"),),
    )
    assert model.resource_names() == frozenset({"api", "db"})
    assert model.service_names() == frozenset({"api"})
    assert model.database_names() == frozenset({"db"})


def test_model_defaults() -> None:
    service = Service(name="api", image="x:1")
    assert service.replicas == 1
    assert service.env == {}
    assert service.public is False
    assert service.user is None
    assert service.resources is None
    assert service.command is None
    database = Database(name="db", engine="postgres")
    assert database.version is None
    assert database.size is None
    assert database.public is False
    assert database.port is None


def test_env_value_and_resources_are_frozen() -> None:
    env = EnvValue("secret", secret=True, line=1, column=2, length=3)
    assert env.secret is True
    resources = Resources(cpu="500m", memory="512Mi")
    assert resources.cpu == "500m"
