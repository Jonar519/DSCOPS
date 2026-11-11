"""Small, dependency-light utilities shared by compiler stages.

The functions here are deliberately pure and free of backend concepts.
"""

from __future__ import annotations

import re

_SENSITIVE_FRAGMENTS = (
    "PASSWORD",
    "PASSWD",
    "PASSPHRASE",
    "SECRET",
    "TOKEN",
    "APIKEY",
    "PRIVATEKEY",
    "ACCESSKEY",
    "CREDENTIAL",
    "AUTHORIZATION",
    "DATABASEURL",
    "DBURL",
    "DSN",
    "CONNECTIONSTRING",
)

_STORAGE_RE = re.compile(
    r"^\s*(?P<amount>\d+(?:\.\d+)?)\s*(?P<unit>[KMGTPE]i?B?|B)?\s*$", re.IGNORECASE
)


def normalize_identifier(value: str) -> str:
    """Normalize an env var or resource name for security comparisons."""

    return re.sub(r"[^A-Z0-9]", "", value.upper())


def is_sensitive_env_key(key: str) -> bool:
    """Return ``True`` when an env var name looks like it holds a secret."""

    normalized = normalize_identifier(key)
    if any(fragment in normalized for fragment in _SENSITIVE_FRAGMENTS):
        return True
    parts = re.split(r"[^A-Z0-9]+", key.upper())
    return "KEY" in parts


def image_tag(image: str) -> str | None:
    """Return the tag of an image reference, or ``None`` when it has no tag.

    A digest reference (``image@sha256:...``) returns the digest, so callers can
    distinguish it from an untagged image.
    """

    reference = image.strip()
    if not reference:
        return None
    if "@" in reference:
        return reference.split("@", 1)[1]
    last_segment = reference.rsplit("/", 1)[-1]
    if ":" in last_segment:
        return last_segment.rsplit(":", 1)[1]
    return None


def is_pinned_image(image: str) -> bool:
    """A pinned image has a non-``latest`` tag or a digest."""

    reference = image.strip()
    if "@" in reference:
        return True
    tag = image_tag(reference)
    return tag is not None and tag.lower() != "latest"


def normalize_storage_size(size: str | None) -> str:
    """Convert a friendly size (``20GB``) to a Kubernetes quantity (``20Gi``).

    Decimal Kubernetes quantities (``20G``) are also valid, but the DSL uses
    ``GB`` in its examples. Keeping the conversion here makes both backends
    agree on the semantics.
    """

    if size is None:
        return "1Gi"
    match = _STORAGE_RE.match(size)
    if match is None:
        return size.strip() or "1Gi"
    amount = match.group("amount")
    unit = (match.group("unit") or "G").upper()
    if unit.startswith("K"):
        return f"{amount}Ki"
    if unit.startswith("M"):
        return f"{amount}Mi"
    if unit.startswith("G"):
        return f"{amount}Gi"
    if unit.startswith("T"):
        return f"{amount}Ti"
    if unit.startswith("P"):
        return f"{amount}Pi"
    if unit.startswith("E"):
        return f"{amount}Ei"
    return f"{amount}"


def env_text(value: str | int | bool) -> str:
    """Serialize a scalar env value the way containers expect it."""

    if isinstance(value, bool):
        return "true" if value else "false"
    return str(value)
