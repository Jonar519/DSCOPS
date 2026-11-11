"""Backend implementations and their registration.

Importing this package wires the built-in backends into the registry. The app
layer only depends on the ``Backend`` protocol and ``get_backend``.
"""

from __future__ import annotations

from dscops.backends.base import Artifact, Backend, TargetInfo
from dscops.backends.compose import ComposeBackend
from dscops.backends.github_actions import GitHubActionsBackend
from dscops.backends.kubernetes import KubernetesBackend
from dscops.backends.registry import (
    UnknownTarget,
    available_targets,
    canonical_target,
    get_backend,
    register,
)
from dscops.backends.terraform import TerraformBackend

register(ComposeBackend(), aliases=("docker", "docker-compose"))
register(KubernetesBackend(), aliases=("k8s",))
register(GitHubActionsBackend(), aliases=("github", "gha"))
register(TerraformBackend(), aliases=("tf",))

__all__ = [
    "Artifact",
    "Backend",
    "TargetInfo",
    "UnknownTarget",
    "available_targets",
    "canonical_target",
    "get_backend",
    "register",
]
