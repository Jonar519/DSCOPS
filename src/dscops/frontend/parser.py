"""Lark-based lexer/parser for the DSCOPS language.

Public contract::

    ast = parse(source)  # SourceFile, or raise ParseError

``ParseError`` carries a domain ``Diagnostic`` so the application layer can
handle syntax errors exactly like semantic or security findings.
"""

from __future__ import annotations

from builtins import object as PyObject
from functools import lru_cache
from pathlib import Path
from typing import cast

from lark import Lark, Token, Transformer, v_args
from lark.exceptions import UnexpectedCharacters, UnexpectedEOF, UnexpectedInput, UnexpectedToken
from lark.tree import Meta

from dscops.domain.ast import (
    BoolValue,
    CallValue,
    DatabaseDecl,
    LinkDecl,
    NameValue,
    NumberValue,
    ObjectValue,
    Pair,
    Property,
    ServiceDecl,
    SourceFile,
    SourceLocation,
    Statement,
    StringValue,
    Value,
)
from dscops.domain.diagnostics import Diagnostic, Severity

_GRAMMAR_PATH = Path(__file__).with_name("grammar.lark")


class ParseError(Exception):
    """A source file could not be parsed."""

    def __init__(self, diagnostic: Diagnostic) -> None:
        super().__init__(diagnostic.message)
        self.diagnostic = diagnostic


@lru_cache(maxsize=1)
def _parser() -> Lark:
    return Lark(
        _GRAMMAR_PATH.read_text(encoding="utf-8"),
        parser="lalr",
        propagate_positions=True,
        maybe_placeholders=False,
        start="start",
    )


def _token_location(token: Token) -> SourceLocation:
    line = int(token.line or 1)
    column = int(token.column or 1)
    end_column = int(token.end_column or column)
    return SourceLocation(line=line, column=column, length=max(1, end_column - column))


def _meta_location(meta: Meta) -> SourceLocation:
    line = int(meta.line or 1)
    column = int(meta.column or 1)
    end_column = int(meta.end_column or column)
    return SourceLocation(line=line, column=column, length=max(1, end_column - column))


def _as_token(value: object) -> Token:
    if not isinstance(value, Token):
        raise TypeError(f"expected a token, got {type(value).__name__}")
    return value


def _as_property(value: object) -> Property:
    if not isinstance(value, Property):
        raise TypeError(f"expected a property, got {type(value).__name__}")
    return value


def _as_pair(value: object) -> Pair:
    if not isinstance(value, Pair):
        raise TypeError(f"expected a pair, got {type(value).__name__}")
    return value


def _as_statement(value: object) -> Statement:
    if isinstance(value, (ServiceDecl, DatabaseDecl, LinkDecl)):
        return value
    raise TypeError(f"expected a statement, got {type(value).__name__}")


def _as_value(value: object) -> Value:
    if isinstance(value, (StringValue, NumberValue, BoolValue, NameValue, CallValue, ObjectValue)):
        return value
    raise TypeError(f"expected a value, got {type(value).__name__}")


@v_args(meta=True)
class _AstBuilder(Transformer[Token, object]):
    """Turn Lark's parse tree into the small, typed DSCOPS AST."""

    def start(self, meta: Meta, children: list[PyObject]) -> SourceFile:
        statements = tuple(_as_statement(child) for child in children)
        location = SourceLocation(1, 1, 1) if meta.empty else _meta_location(meta)
        return SourceFile(location=location, statements=statements)

    def service(self, meta: Meta, children: list[PyObject]) -> ServiceDecl:
        name = _as_token(children[0]).value
        properties = tuple(_as_property(child) for child in children[1:])
        return ServiceDecl(location=_meta_location(meta), name=name, properties=properties)

    def database(self, meta: Meta, children: list[PyObject]) -> DatabaseDecl:
        name = _as_token(children[0]).value
        properties = tuple(_as_property(child) for child in children[1:])
        return DatabaseDecl(location=_meta_location(meta), name=name, properties=properties)

    def link(self, meta: Meta, children: list[PyObject]) -> LinkDecl:
        source = _as_token(children[0]).value
        target = _as_token(children[1]).value
        return LinkDecl(location=_meta_location(meta), source=source, target=target)

    def property(self, meta: Meta, children: list[PyObject]) -> Property:
        name_token = _as_token(children[0])
        return Property(
            location=_meta_location(meta),
            name=name_token.value,
            value=_as_value(children[1]),
        )

    def pair(self, meta: Meta, children: list[PyObject]) -> Pair:
        key = _as_token(children[0]).value
        return Pair(location=_meta_location(meta), key=key, value=_as_value(children[1]))

    def call(self, meta: Meta, children: list[PyObject]) -> CallValue:
        name_token = _as_token(children[0])
        arguments = tuple(_as_value(child) for child in children[1:])
        return CallValue(
            location=_meta_location(meta),
            name=name_token.value,
            arguments=arguments,
        )

    def object(self, meta: Meta, children: list[PyObject]) -> ObjectValue:
        return ObjectValue(
            location=_meta_location(meta),
            pairs=tuple(_as_pair(child) for child in children),
        )

    def string(self, _meta: Meta, children: list[PyObject]) -> StringValue:
        token = _as_token(children[0])
        return StringValue(location=_token_location(token), value=token.value[1:-1])

    def number(self, _meta: Meta, children: list[PyObject]) -> NumberValue:
        token = _as_token(children[0])
        return NumberValue(location=_token_location(token), value=int(token.value))

    def bool(self, _meta: Meta, children: list[PyObject]) -> BoolValue:
        token = _as_token(children[0])
        return BoolValue(location=_token_location(token), value=token.value == "true")

    def name(self, _meta: Meta, children: list[PyObject]) -> NameValue:
        token = _as_token(children[0])
        return NameValue(location=_token_location(token), value=token.value)


def parse(source: str) -> SourceFile:
    """Parse ``source`` into an AST.

    Raises:
        ParseError: with a ``SYN001`` diagnostic when the input is invalid.
    """

    try:
        tree = _parser().parse(source)
        result = _AstBuilder().transform(tree)
    except UnexpectedCharacters as exc:
        char = exc.char
        diagnostic = Diagnostic(
            code="SYN001",
            severity=Severity.ERROR,
            message=f"carácter inesperado {char!r}",
            line=max(1, int(exc.line or 1)),
            column=max(1, int(exc.column or 1)),
            hint="revisa la sintaxis: se esperaba una declaración, una propiedad o un valor",
            length=1,
        )
        raise ParseError(diagnostic) from exc
    except UnexpectedEOF as exc:
        expected = _format_expected(exc.expected)
        diagnostic = Diagnostic(
            code="SYN001",
            severity=Severity.ERROR,
            message="fin de archivo inesperado",
            line=max(1, int(exc.line or 1)),
            column=max(1, int(exc.column or 1)),
            hint=f"revisa si falta cerrar una llave o un valor; se esperaba: {expected}",
            length=1,
        )
        raise ParseError(diagnostic) from exc
    except UnexpectedToken as exc:
        token = exc.token
        expected = _format_expected(exc.expected)
        shown = "fin de archivo" if token.type == "$END" else repr(str(token))
        diagnostic = Diagnostic(
            code="SYN001",
            severity=Severity.ERROR,
            message=f"token inesperado {shown}",
            line=max(1, int(token.line or exc.line or 1)),
            column=max(1, int(token.column or exc.column or 1)),
            hint=f"se esperaba: {expected}",
            length=max(1, len(str(token))),
        )
        raise ParseError(diagnostic) from exc
    except UnexpectedInput as exc:  # pragma: no cover - defensive fallback
        diagnostic = Diagnostic(
            code="SYN001",
            severity=Severity.ERROR,
            message="no se pudo interpretar el archivo",
            line=max(1, int(getattr(exc, "line", 1) or 1)),
            column=max(1, int(getattr(exc, "column", 1) or 1)),
            hint="revisa la sintaxis del archivo",
        )
        raise ParseError(diagnostic) from exc

    if not isinstance(result, SourceFile):
        raise TypeError("the parser produced an unexpected root node")
    return result


def _format_expected(expected: object) -> str:
    if not expected:
        return "una construcción válida"
    names = sorted(str(item) for item in cast(list[object], expected))
    readable = []
    for name in names:
        if name == "NAME":
            readable.append("un identificador")
        elif name == "STRING":
            readable.append("una cadena")
        elif name == "NUMBER":
            readable.append("un número")
        elif name == "BOOL":
            readable.append("true o false")
        elif name == "$END":
            readable.append("fin de archivo")
        elif name.startswith("__"):
            continue
        else:
            readable.append(name)
    if not readable:
        return "una construcción válida"
    if len(readable) == 1:
        return readable[0]
    return ", ".join(readable[:-1]) + " o " + readable[-1]
