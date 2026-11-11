"""Public domain contracts.

Importing this package is cheap: it only exposes dataclasses and enums.
"""

from __future__ import annotations

from dscops.domain.diagnostics import (
    Diagnostic,
    Severity,
    count_by_severity,
    format_location,
    has_errors,
)
from dscops.domain.model import Database, EnvValue, InfraModel, Link, Resources, Service

__all__ = [
    "Database",
    "Diagnostic",
    "EnvValue",
    "InfraModel",
    "Link",
    "Resources",
    "Service",
    "Severity",
    "count_by_severity",
    "format_location",
    "has_errors",
]
