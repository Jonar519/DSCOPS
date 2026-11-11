"""GitHub Actions backend: a ready-to-commit security gate workflow."""

from __future__ import annotations

from typing import Any

from dscops.backends._yaml import dump_yaml
from dscops.backends.base import Artifact
from dscops.domain.model import InfraModel


class GitHubActionsBackend:
    name = "github-actions"
    description = "GitHub Actions workflow (.github/workflows/dscops.yml)"

    def generate(self, model: InfraModel) -> list[Artifact]:
        workflow = _workflow(model)
        return [
            Artifact(
                path=".github/workflows/dscops.yml",
                content=dump_yaml(workflow),
            )
        ]


def _workflow(model: InfraModel) -> dict[str, Any]:
    resources = len(model.services) + len(model.databases)
    return {
        "name": "DSCOPS security gate",
        "on": {
            "push": {"branches": ["main"]},
            "pull_request": {},
            "workflow_dispatch": {},
        },
        "permissions": {"contents": "read"},
        "concurrency": {
            "group": "dscops-${{ github.ref }}",
            "cancel-in-progress": True,
        },
        "jobs": {
            "verify": {
                "name": f"Check and build {resources} resources",
                "runs-on": "ubuntu-latest",
                "timeout-minutes": 10,
                "steps": [
                    {"uses": "actions/checkout@v4"},
                    {
                        "name": "Set up Python",
                        "uses": "actions/setup-python@v5",
                        "with": {"python-version": "3.12", "cache": "pip"},
                    },
                    {
                        "name": "Install DSCOPS",
                        "run": "python -m pip install --upgrade pip && pip install .",
                    },
                    {
                        "name": "Validate examples",
                        "run": "dscops check examples/*.dscops",
                    },
                    {
                        "name": "Build deployment artifacts",
                        "run": (
                            "dscops build examples/app.dscops "
                            "--target compose,kubernetes --out dist"
                        ),
                    },
                    {
                        "name": "Upload artifacts",
                        "uses": "actions/upload-artifact@v4",
                        "with": {
                            "name": "dscops-artifacts",
                            "path": "dist/",
                            "if-no-files-found": "error",
                            "include-hidden-files": True,
                        },
                    },
                ],
            }
        },
    }
