"""Abstract syntax tree produced by the DSCOPS frontend.

The AST is a faithful, low-level representation of the source file. It knows
which properties were written and where; it does *not* know what they mean.
Interpreting and validating the AST is the job of ``dscops.semantic``.
"""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True, slots=True)
class SourceLocation:
    """A 1-based source position with an optional token length."""

    line: int
    column: int
    length: int = 1


@dataclass(frozen=True, slots=True)
class StringValue:
    location: SourceLocation
    value: str


@dataclass(frozen=True, slots=True)
class NumberValue:
    location: SourceLocation
    value: int


@dataclass(frozen=True, slots=True)
class BoolValue:
    location: SourceLocation
    value: bool


@dataclass(frozen=True, slots=True)
class NameValue:
    location: SourceLocation
    value: str


@dataclass(frozen=True, slots=True)
class CallValue:
    location: SourceLocation
    name: str
    arguments: tuple[Value, ...]


@dataclass(frozen=True, slots=True)
class ObjectValue:
    location: SourceLocation
    pairs: tuple[Pair, ...]


type Value = StringValue | NumberValue | BoolValue | NameValue | CallValue | ObjectValue


@dataclass(frozen=True, slots=True)
class Pair:
    """A key/value pair inside an object literal."""

    location: SourceLocation
    key: str
    value: Value


@dataclass(frozen=True, slots=True)
class Property:
    """A ``name: value`` property inside a resource declaration."""

    location: SourceLocation
    name: str
    value: Value


@dataclass(frozen=True, slots=True)
class ServiceDecl:
    location: SourceLocation
    name: str
    properties: tuple[Property, ...]


@dataclass(frozen=True, slots=True)
class DatabaseDecl:
    location: SourceLocation
    name: str
    properties: tuple[Property, ...]


@dataclass(frozen=True, slots=True)
class LinkDecl:
    location: SourceLocation
    source: str
    target: str


type Statement = ServiceDecl | DatabaseDecl | LinkDecl


@dataclass(frozen=True, slots=True)
class SourceFile:
    """The root of every parsed ``.dscops`` file."""

    location: SourceLocation
    statements: tuple[Statement, ...]


# ``ObjectValue`` references ``Pair`` before it is defined; that is fine with
# postponed annotations, but keeping the alias below makes the public API clear.
type Node = SourceFile | Statement | Property | Pair | Value
