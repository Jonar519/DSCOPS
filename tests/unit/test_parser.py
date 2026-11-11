"""Frontend tests: lexer, parser, AST locations and syntax diagnostics."""

from __future__ import annotations

import pytest

from dscops.domain.ast import (
    BoolValue,
    CallValue,
    DatabaseDecl,
    LinkDecl,
    NameValue,
    NumberValue,
    ObjectValue,
    ServiceDecl,
    StringValue,
)
from dscops.frontend import ParseError, parse


def test_parse_full_example(valid_source: str) -> None:
    ast = parse(valid_source)
    assert len(ast.statements) == 7
    services = [item for item in ast.statements if isinstance(item, ServiceDecl)]
    databases = [item for item in ast.statements if isinstance(item, DatabaseDecl)]
    links = [item for item in ast.statements if isinstance(item, LinkDecl)]
    assert [service.name for service in services] == ["api", "worker"]
    assert [database.name for database in databases] == ["main", "cache"]
    assert [(link.source, link.target) for link in links] == [
        ("api", "main"),
        ("api", "cache"),
        ("worker", "main"),
    ]


def test_empty_file_and_comments() -> None:
    assert parse("").statements == ()
    assert parse("# just a comment\n\n# another\n").statements == ()


def test_comment_after_statement_is_ignored() -> None:
    ast = parse('service api { image: "x:1" } # trailing\n')
    assert len(ast.statements) == 1


def test_hash_inside_string_is_not_a_comment() -> None:
    ast = parse('service api { image: "repo/app#fragment:1" }')
    service = ast.statements[0]
    assert isinstance(service, ServiceDecl)
    image = service.properties[0].value
    assert isinstance(image, StringValue)
    assert image.value == "repo/app#fragment:1"


def test_scalar_values_and_positions() -> None:
    ast = parse(
        "service s {\n"
        '  image: "x:1"\n'
        "  port: 8080\n"
        "  replicas: 2\n"
        "  expose: public\n"
        "  debug: true\n"
        "}\n"
    )
    service = ast.statements[0]
    assert isinstance(service, ServiceDecl)
    values = [prop.value for prop in service.properties]
    assert isinstance(values[0], StringValue)
    assert isinstance(values[1], NumberValue)
    assert values[1].value == 8080
    assert isinstance(values[3], NameValue)
    assert values[3].value == "public"
    assert isinstance(values[4], BoolValue)
    assert values[4].value is True
    assert values[1].location.line == 3
    assert values[1].location.column == 9


def test_object_and_call_values() -> None:
    ast = parse(
        'service s {\n  image: "x:1"\n  env: { DB_URL: secret("db_url"), DEBUG: false }\n}\n'
    )
    service = ast.statements[0]
    assert isinstance(service, ServiceDecl)
    env = service.properties[1].value
    assert isinstance(env, ObjectValue)
    assert [pair.key for pair in env.pairs] == ["DB_URL", "DEBUG"]
    first = env.pairs[0].value
    assert isinstance(first, CallValue)
    assert first.name == "secret"
    assert isinstance(first.arguments[0], StringValue)
    assert first.arguments[0].value == "db_url"
    assert isinstance(env.pairs[1].value, BoolValue)
    assert env.pairs[1].value.value is False


def test_empty_object_and_call_without_arguments() -> None:
    ast = parse('service s {\n  image: "x:1"\n  env: {}\n  metadata: build()\n}\n')
    service = ast.statements[0]
    assert isinstance(service, ServiceDecl)
    env = service.properties[1].value
    call = service.properties[2].value
    assert isinstance(env, ObjectValue)
    assert env.pairs == ()
    assert isinstance(call, CallValue)
    assert call.arguments == ()


def test_nested_object_parses_in_frontend() -> None:
    ast = parse('service s {\n  image: "x:1"\n  env: { NESTED: { A: 1, B: "two" } }\n}\n')
    service = ast.statements[0]
    assert isinstance(service, ServiceDecl)
    env = service.properties[1].value
    assert isinstance(env, ObjectValue)
    nested = env.pairs[0].value
    assert isinstance(nested, ObjectValue)
    assert len(nested.pairs) == 2


def test_database_and_link_locations() -> None:
    ast = parse("database db {\n  engine: postgres\n}\napi -> db\n")
    database = ast.statements[0]
    link = ast.statements[1]
    assert isinstance(database, DatabaseDecl)
    assert database.location.line == 1
    assert isinstance(link, LinkDecl)
    assert link.location.line == 4
    assert link.location.column == 1


def test_one_line_service() -> None:
    ast = parse('service api { image: "x:1" port: 80 }')
    service = ast.statements[0]
    assert isinstance(service, ServiceDecl)
    assert len(service.properties) == 2


@pytest.mark.parametrize(
    ("source", "code"),
    [
        ("service api {", "SYN001"),
        ("service api { image: }", "SYN001"),
        ('service api { image: "x:1" } ?', "SYN001"),
        ("}", "SYN001"),
        ("database db { engine: }", "SYN001"),
        ('service api { image: "x:1" ', "SYN001"),
    ],
)
def test_syntax_errors_are_diagnostics(source: str, code: str) -> None:
    with pytest.raises(ParseError) as captured:
        parse(source)
    diagnostic = captured.value.diagnostic
    assert diagnostic.code == code
    assert diagnostic.line is not None
    assert diagnostic.line >= 1
    assert diagnostic.column is not None
    assert diagnostic.column >= 1
    assert diagnostic.hint


def test_unexpected_character_message() -> None:
    with pytest.raises(ParseError) as captured:
        parse("service api { image: @ }")
    assert "carácter inesperado" in captured.value.diagnostic.message


def test_unexpected_eof_message() -> None:
    with pytest.raises(ParseError) as captured:
        parse("service api { image: ")
    diagnostic = captured.value.diagnostic
    assert "fin de archivo" in diagnostic.message


def test_unexpected_token_message() -> None:
    with pytest.raises(ParseError) as captured:
        parse("service api { image: }")
    diagnostic = captured.value.diagnostic
    assert "token inesperado" in diagnostic.message


def test_bool_is_not_parsed_as_name() -> None:
    ast = parse('service s { image: "x:1" flag: true }')
    service = ast.statements[0]
    assert isinstance(service, ServiceDecl)
    assert isinstance(service.properties[1].value, BoolValue)
