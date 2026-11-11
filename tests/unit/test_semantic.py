"""Semantic analysis tests: every check gets at least one positive and one negative case."""

from __future__ import annotations

from dscops.domain.ast import SourceFile
from dscops.frontend import parse
from dscops.semantic import build_model


def analyze(source: str) -> tuple[object, list[str]]:
    result = build_model(parse(source))
    return result.model, [diagnostic.code for diagnostic in result.diagnostics]


def test_valid_model() -> None:
    source = (
        "service api {\n"
        '  image: "python:3.12-slim"\n'
        "  port: 8000\n"
        "  replicas: 3\n"
        '  env: { DEBUG: false, COUNT: 2, NAME: app, DB_URL: secret("db_url") }\n'
        "  expose: public\n"
        '  user: "10001:10001"\n'
        '  resources: { cpu: "500m", memory: "512Mi" }\n'
        '  command: "python -m http.server 8000"\n'
        "}\n"
        'database main { engine: postgres version: "16" size: "20GB" }\n'
        "api -> main\n"
    )
    model, codes = analyze(source)
    assert codes == []
    assert model.services[0].replicas == 3  # type: ignore[union-attr]
    assert model.services[0].env["DEBUG"].value == "false"  # type: ignore[union-attr]
    assert model.services[0].env["COUNT"].value == "2"  # type: ignore[union-attr]
    assert model.services[0].env["NAME"].value == "app"  # type: ignore[union-attr]
    assert model.services[0].env["DB_URL"].secret is True  # type: ignore[union-attr]
    assert model.databases[0].port is None  # type: ignore[union-attr]
    assert model.links[0].target == "main"  # type: ignore[union-attr]


def test_defaults() -> None:
    model, codes = analyze('service api { image: "x:1" }\ndatabase db { engine: postgres }')
    assert codes == []
    service = model.services[0]  # type: ignore[union-attr]
    assert service.port is None
    assert service.replicas == 1
    assert service.public is False
    assert service.user is None
    assert service.resources is None
    assert service.command is None
    database = model.databases[0]  # type: ignore[union-attr]
    assert database.version is None
    assert database.size is None
    assert database.public is False


def test_forward_reference_is_allowed() -> None:
    model, codes = analyze(
        'api -> main\nservice api { image: "x:1" }\ndatabase main { engine: postgres }'
    )
    assert codes == []
    assert len(model.links) == 1  # type: ignore[union-attr]


def test_duplicate_resources() -> None:
    source = (
        'service api { image: "x:1" }\n'
        'service api { image: "x:2" }\n'
        "database api { engine: postgres }\n"
    )
    model, codes = analyze(source)
    assert codes.count("SEC009") == 2
    assert len(model.services) == 1  # type: ignore[union-attr]
    assert len(model.databases) == 0  # type: ignore[union-attr]


def test_dangling_link_target_and_source() -> None:
    model, codes = analyze('service api { image: "x:1" }\nghost -> api\napi -> missing\n')
    assert codes.count("SEC008") == 2
    assert model.links == ()  # type: ignore[union-attr]


def test_missing_image_and_engine() -> None:
    model, codes = analyze("service api {}\ndatabase db {}")
    assert codes.count("SEM001") == 2
    assert model.services[0].image == ""  # type: ignore[union-attr]
    assert model.databases[0].engine == ""  # type: ignore[union-attr]


def test_image_must_be_a_nonempty_string() -> None:
    _, codes = analyze("service api { image: 123 }")
    assert "SEM002" in codes
    _, codes = analyze('service api { image: "" }')
    assert "SEM002" in codes


def test_invalid_ports_and_replicas() -> None:
    _, codes = analyze('service api { image: "x:1" port: "8000" }')
    assert "SEM002" in codes
    _, codes = analyze('service api { image: "x:1" port: 0 }')
    assert "SEM002" in codes
    _, codes = analyze('service api { image: "x:1" port: 70000 }')
    assert "SEM002" in codes
    _, codes = analyze('service api { image: "x:1" replicas: 0 }')
    assert "SEM002" in codes
    _, codes = analyze('service api { image: "x:1" replicas: "3" }')
    assert "SEM002" in codes
    _, codes = analyze('service api { image: "x:1" replicas: 1001 }')
    assert "SEM002" in codes


def test_duplicate_and_unknown_properties() -> None:
    _, codes = analyze('service api { image: "x:1" image: "x:2" colour: blue }')
    assert "SEM003" in codes
    assert "SEM004" in codes


def test_unknown_database_property() -> None:
    _, codes = analyze("database db { engine: postgres password: nope }")
    assert "SEM004" in codes


def test_env_must_be_an_object() -> None:
    _, codes = analyze('service api { image: "x:1" env: "nope" }')
    assert "SEM002" in codes


def test_nested_object_in_env_is_rejected() -> None:
    _, codes = analyze('service api { image: "x:1" env: { A: { B: 1 } } }')
    assert "SEM002" in codes


def test_duplicate_env_key() -> None:
    _, codes = analyze('service api { image: "x:1" env: { A: 1, A: 2 } }')
    assert "SEM003" in codes


def test_secret_call_variants() -> None:
    _, codes = analyze('service api { image: "x:1" env: { A: secret() } }')
    assert "SEM005" in codes
    _, codes = analyze('service api { image: "x:1" env: { A: secret(1) } }')
    assert "SEM005" in codes
    _, codes = analyze('service api { image: "x:1" env: { A: secret("") } }')
    assert "SEM005" in codes
    _, codes = analyze('service api { image: "x:1" env: { A: unknown("x") } }')
    assert "SEM005" in codes


def test_expose_validation() -> None:
    model, codes = analyze('service api { image: "x:1" expose: private }')
    assert model.services[0].public is False  # type: ignore[union-attr]
    assert codes == []
    model, codes = analyze('service api { image: "x:1" expose: true }')
    assert model.services[0].public is True  # type: ignore[union-attr]
    assert codes == []
    model, codes = analyze('service api { image: "x:1" expose: "public" }')
    assert model.services[0].public is True  # type: ignore[union-attr]
    assert codes == []
    _, codes = analyze('service api { image: "x:1" expose: maybe }')
    assert "SEM002" in codes


def test_resources_validation() -> None:
    model, codes = analyze('service api { image: "x:1" resources: { cpu: 500, memory: "512Mi" } }')
    assert codes == []
    assert model.services[0].resources.cpu == "500"  # type: ignore[union-attr]
    _, codes = analyze('service api { image: "x:1" resources: "bad" }')
    assert "SEM002" in codes
    _, codes = analyze('service api { image: "x:1" resources: { gpu: "1" } }')
    assert "SEM004" in codes
    _, codes = analyze('service api { image: "x:1" resources: { cpu: "1", cpu: "2" } }')
    assert "SEM003" in codes
    _, codes = analyze('service api { image: "x:1" resources: { cpu: true } }')
    assert "SEM002" in codes


def test_empty_user_and_command() -> None:
    _, codes = analyze('service api { image: "x:1" user: "" }')
    assert "SEM002" in codes
    _, codes = analyze('service api { image: "x:1" command: "" }')
    assert "SEM002" in codes
    _, codes = analyze('service api { image: "x:1" command: 3 }')
    assert "SEM002" in codes


def test_database_property_types() -> None:
    model, codes = analyze(
        'database db { engine: postgres version: 16 size: "10GB" port: 5433 expose: public }'
    )
    assert codes == []
    assert model.databases[0].version == "16"  # type: ignore[union-attr]
    assert model.databases[0].port == 5433  # type: ignore[union-attr]
    assert model.databases[0].public is True  # type: ignore[union-attr]
    _, codes = analyze("database db { engine: 1 }")
    assert "SEM002" in codes
    _, codes = analyze('database db { engine: "" }')
    assert "SEM002" in codes
    _, codes = analyze("database db { engine: postgres size: 10 }")
    assert "SEM002" in codes
    _, codes = analyze("database db { engine: postgres port: 0 }")
    assert "SEM002" in codes
    _, codes = analyze("database db { engine: postgres expose: weird }")
    assert "SEM002" in codes


def test_empty_source_produces_empty_model() -> None:
    result = build_model(parse(""))
    assert isinstance(parse(""), SourceFile)
    assert result.model.services == ()
    assert result.model.databases == ()
    assert result.model.links == ()
    assert result.diagnostics == ()


def test_property_map_keeps_first_duplicate() -> None:
    model, codes = analyze('service api { image: "first:1" image: "second:1" }')
    assert "SEM003" in codes
    assert model.services[0].image == "first:1"  # type: ignore[union-attr]
