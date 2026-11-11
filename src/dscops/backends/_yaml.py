"""YAML serialization helper. YAML always comes from data structures, never strings."""

from __future__ import annotations

from typing import Any

import yaml


def dump_yaml(data: dict[str, Any]) -> str:
    return str(
        yaml.safe_dump(
            data,
            sort_keys=False,
            default_flow_style=False,
            allow_unicode=True,
            width=100,
        )
    )


def dump_yaml_documents(documents: list[dict[str, Any]]) -> str:
    if not documents:
        return ""
    return str(
        yaml.safe_dump_all(
            documents,
            sort_keys=False,
            default_flow_style=False,
            allow_unicode=True,
            width=100,
            explicit_start=False,
        )
    )
