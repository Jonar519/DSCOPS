"""Terraform backend for the Docker provider.

HCL is the one output format where a text template is a better fit than a
dictionary. Jinja2 keeps the template readable while Python builds the model.
"""

from __future__ import annotations

import re
from pathlib import Path
from typing import Any

from jinja2 import Environment, StrictUndefined

from dscops.backends._common import (
    database_data_path,
    database_image,
    database_password_variable,
    database_port,
    terraform_identifier,
)
from dscops.backends.base import Artifact
from dscops.domain.model import Database, EnvValue, InfraModel, Service

_TEMPLATE_PATH = Path(__file__).with_name("templates") / "terraform_main.tf.j2"


class TerraformBackend:
    name = "terraform"
    description = "Terraform with the Docker provider (terraform/main.tf)"

    def generate(self, model: InfraModel) -> list[Artifact]:
        secret_vars = _SecretVariables(model)
        context = {
            "secret_variables": [{"name": name} for name in sorted(secret_vars.by_variable)],
            "services": [
                _service_context(service, model, secret_vars) for service in model.services
            ],
            "databases": [_database_context(database, secret_vars) for database in model.databases],
        }
        environment = Environment(
            undefined=StrictUndefined,
            autoescape=False,
            trim_blocks=True,
            lstrip_blocks=True,
            keep_trailing_newline=True,
        )
        template = environment.from_string(_TEMPLATE_PATH.read_text(encoding="utf-8"))
        return [Artifact(path="terraform/main.tf", content=template.render(**context))]


class _SecretVariables:
    """Assign a stable, unique Terraform variable to every external secret."""

    def __init__(self, model: InfraModel) -> None:
        self.by_variable: dict[str, str] = {}
        for service in model.services:
            for value in service.env.values():
                if value.secret:
                    self._register(value.value)
        for database in model.databases:
            self._register(database_password_variable(database))

    def _register(self, secret: str) -> str:
        base = terraform_identifier(secret)
        candidate = base
        counter = 2
        while candidate in self.by_variable:
            if self.by_variable[candidate] == secret:
                return candidate
            candidate = f"{base}_{counter}"
            counter += 1
        self.by_variable[candidate] = secret
        return candidate

    def variable_for(self, secret: str) -> str:
        return self._register(secret)


def _hcl_quote(value: str) -> str:
    escaped = (
        value.replace("\\", "\\\\").replace('"', '\\"').replace("${", "$${").replace("%{", "%%{")
    )
    return f'"{escaped}"'


def _secret_expression(name: str) -> str:
    return f"${{var.{name}}}"


def _env_item(key: str, value: EnvValue, secret_vars: _SecretVariables) -> str:
    if value.secret:
        variable = secret_vars.variable_for(value.value)
        return f'"{key}={_secret_expression(variable)}"'
    return _hcl_quote(f"{key}={value.value}")


def _service_context(
    service: Service,
    model: InfraModel,
    secret_vars: _SecretVariables,
) -> dict[str, Any]:
    dependencies: list[str] = []
    database_names = model.database_names()
    for link in model.links:
        if link.source != service.name:
            continue
        if link.target in database_names:
            dependencies.append(f"docker_container.database_{terraform_identifier(link.target)}")
        elif link.target in model.service_names():
            dependencies.append(f"docker_container.service_{terraform_identifier(link.target)}")
    return {
        "key": terraform_identifier(service.name),
        "name": service.name,
        "image": service.image,
        "replicas": service.replicas,
        "public": service.public,
        "port": service.port,
        "env": [_env_item(key, value, secret_vars) for key, value in service.env.items()],
        "memory_mb": _memory_mb(service),
        "command": _service_command(service),
        "depends_on": dependencies,
    }


def _service_command(service: Service) -> list[str]:
    if not service.command:
        return []
    return [_hcl_quote("sh"), _hcl_quote("-c"), _hcl_quote(service.command)]


def _database_context(database: Database, secret_vars: _SecretVariables) -> dict[str, Any]:
    password_variable = secret_vars.variable_for(database_password_variable(database))
    engine = database.engine
    env: list[str] = []
    command: list[str] = []
    if engine in {"postgres", "postgresql"}:
        env = [
            _hcl_quote(f"POSTGRES_USER={database.name}"),
            f'"POSTGRES_PASSWORD={_secret_expression(password_variable)}"',
            _hcl_quote(f"POSTGRES_DB={database.name}"),
        ]
    elif engine in {"mysql", "mariadb"}:
        env = [
            f'"MYSQL_ROOT_PASSWORD={_secret_expression(password_variable)}"',
            _hcl_quote(f"MYSQL_DATABASE={database.name}"),
        ]
    elif engine in {"mongodb", "mongo"}:
        env = [
            _hcl_quote(f"MONGO_INITDB_ROOT_USERNAME={database.name}"),
            f'"MONGO_INITDB_ROOT_PASSWORD={_secret_expression(password_variable)}"',
            _hcl_quote(f"MONGO_INITDB_DATABASE={database.name}"),
        ]
    elif engine == "redis":
        env = [f'"REDIS_PASSWORD={_secret_expression(password_variable)}"']
        command = [
            _hcl_quote("redis-server"),
            _hcl_quote("--requirepass"),
            f'"${{var.{password_variable}}}"',
        ]
    return {
        "key": terraform_identifier(database.name),
        "name": database.name,
        "image": database_image(database),
        "public": database.public,
        "port": database_port(database),
        "env": env,
        "command": command,
        "data_path": database_data_path(database),
    }


def _memory_mb(service: Service) -> int | None:
    if service.resources is None or not service.resources.memory:
        return None
    match = re.fullmatch(r"\s*(\d+)\s*([KMG]i?B?)?\s*", service.resources.memory, re.IGNORECASE)
    if match is None:
        return None
    amount = int(match.group(1))
    unit = (match.group(2) or "M").upper()
    if unit.startswith("K"):
        return max(1, amount // 1024)
    if unit.startswith("G"):
        return amount * 1024
    return amount
