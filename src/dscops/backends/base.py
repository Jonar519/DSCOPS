"""Backend port and artifact value objects."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Protocol

from dscops.domain.model import InfraModel


@dataclass(frozen=True, slots=True)
class Artifact:
    """A generated file: relative path plus complete UTF-8 content."""

    path: str
    content: str


class Backend(Protocol):
    """Port implemented by every output backend."""

    name: str
    description: str

    def generate(self, model: InfraModel) -> list[Artifact]: ...


@dataclass(frozen=True, slots=True)
class TargetInfo:
    name: str
    description: str
    aliases: tuple[str, ...] = ()
