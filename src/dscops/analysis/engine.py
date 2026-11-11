"""Security analysis engine.

Adding a rule is a two-step, open/closed operation: create a module with a
class that respects ``Rule`` and append an instance to ``RULES``. Nothing else
in the compiler needs to change.
"""

from __future__ import annotations

from typing import Protocol

from dscops.analysis.rules.sec001_hardcoded_secret import HardcodedSecretRule
from dscops.analysis.rules.sec002_image_tag import ImageTagRule
from dscops.analysis.rules.sec003_public_database import PublicDatabaseRule
from dscops.analysis.rules.sec004_public_port import PublicPortRule
from dscops.analysis.rules.sec005_single_replica import SingleReplicaRule
from dscops.analysis.rules.sec006_root_user import RootUserRule
from dscops.analysis.rules.sec007_resource_limits import ResourceLimitsRule
from dscops.analysis.rules.sec010_public_debug import PublicDebugRule
from dscops.domain.diagnostics import Diagnostic
from dscops.domain.model import InfraModel


class Rule(Protocol):
    """Port implemented by every security rule."""

    code: str

    def check(self, model: InfraModel) -> list[Diagnostic]: ...


RULES: tuple[Rule, ...] = (
    HardcodedSecretRule(),
    ImageTagRule(),
    PublicDatabaseRule(),
    PublicPortRule(),
    SingleReplicaRule(),
    RootUserRule(),
    ResourceLimitsRule(),
    PublicDebugRule(),
)


def run_rules(model: InfraModel, rules: tuple[Rule, ...] = RULES) -> list[Diagnostic]:
    """Run every rule against ``model`` and concatenate the findings."""

    diagnostics: list[Diagnostic] = []
    for rule in rules:
        diagnostics.extend(rule.check(model))
    return diagnostics


def rule_codes() -> tuple[str, ...]:
    return tuple(rule.code for rule in RULES)
