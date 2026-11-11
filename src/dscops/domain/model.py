"""Neutral intermediate representation (IR) of a DSCOPS program.

Nothing in this module knows about Docker, Kubernetes, GitHub Actions or
Terraform. Backends consume this model and translate it to their own format.
"""

from __future__ import annotations

from dataclasses import dataclass, field


@dataclass(frozen=True, slots=True)
class EnvValue:
    """A resolved environment variable.

    ``secret=True`` means the source used ``secret("name")``; ``value`` is then
    the name of the externally-managed secret, never its content.
    """

    value: str
    secret: bool = False
    line: int | None = None
    column: int | None = None
    length: int | None = None


@dataclass(frozen=True, slots=True)
class Resources:
    """Container resource limits. Either value may be missing."""

    cpu: str | None = None
    memory: str | None = None


@dataclass(frozen=True, slots=True)
class Service:
    name: str
    image: str
    port: int | None = None
    replicas: int = 1
    env: dict[str, EnvValue] = field(default_factory=dict)
    public: bool = False
    user: str | None = None
    resources: Resources | None = None
    command: str | None = None
    line: int | None = None
    column: int | None = None


@dataclass(frozen=True, slots=True)
class Database:
    name: str
    engine: str
    version: str | None = None
    size: str | None = None
    public: bool = False
    port: int | None = None
    line: int | None = None
    column: int | None = None


@dataclass(frozen=True, slots=True)
class Link:
    source: str
    target: str
    line: int | None = None
    column: int | None = None


@dataclass(frozen=True, slots=True)
class InfraModel:
    services: tuple[Service, ...] = ()
    databases: tuple[Database, ...] = ()
    links: tuple[Link, ...] = ()

    def resource_names(self) -> frozenset[str]:
        """Every declared service and database name."""

        return frozenset(service.name for service in self.services) | frozenset(
            database.name for database in self.databases
        )

    def service_names(self) -> frozenset[str]:
        return frozenset(service.name for service in self.services)

    def database_names(self) -> frozenset[str]:
        return frozenset(database.name for database in self.databases)
