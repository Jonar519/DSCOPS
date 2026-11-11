"""A deliberately simple backend registry (a dictionary is enough)."""

from __future__ import annotations

from dataclasses import dataclass

from dscops.backends.base import Backend, TargetInfo


class UnknownTarget(Exception):
    """The caller asked for a backend that does not exist."""

    def __init__(self, name: str, available: list[str]) -> None:
        super().__init__(f"target desconocido: '{name}'")
        self.name = name
        self.available = available


@dataclass(frozen=True, slots=True)
class _Entry:
    backend: Backend
    aliases: tuple[str, ...]


_BACKENDS: dict[str, _Entry] = {}


def register(backend: Backend, *, aliases: tuple[str, ...] = ()) -> None:
    """Register a backend under its canonical name plus optional aliases."""

    if backend.name in _BACKENDS:
        raise ValueError(f"backend já registrado: {backend.name}")
    _BACKENDS[backend.name] = _Entry(backend=backend, aliases=aliases)


def available_targets() -> tuple[TargetInfo, ...]:
    return tuple(
        TargetInfo(name=name, description=entry.backend.description, aliases=entry.aliases)
        for name, entry in _BACKENDS.items()
    )


def get_backend(name: str) -> Backend:
    """Resolve a target name or alias, or raise ``UnknownTarget``."""

    normalized = name.strip().lower()
    if normalized in _BACKENDS:
        return _BACKENDS[normalized].backend
    for canonical, entry in _BACKENDS.items():
        if normalized in entry.aliases:
            return _BACKENDS[canonical].backend
    raise UnknownTarget(name, list(_BACKENDS))


def canonical_target(name: str) -> str:
    """Return the registered name for an alias, or raise ``UnknownTarget``."""

    normalized = name.strip().lower()
    if normalized in _BACKENDS:
        return normalized
    for canonical, entry in _BACKENDS.items():
        if normalized in entry.aliases:
            return canonical
    raise UnknownTarget(name, list(_BACKENDS))


def reset_registry_for_tests() -> None:  # pragma: no cover - only used by tests
    """Clear the registry. Tests that exercise registration use this."""

    _BACKENDS.clear()
