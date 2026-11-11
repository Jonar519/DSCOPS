"""Docker Compose backend.

The output is a dictionary serialized with PyYAML. No indentation-sensitive
text templates are involved.
"""

from __future__ import annotations

import re
from typing import Any

from dscops.backends._common import (
    DEFAULT_CONTAINER_USER,
    database_data_path,
    database_image,
    database_password_variable,
    database_port,
    sanitize_variable,
)
from dscops.backends._yaml import dump_yaml
from dscops.backends.base import Artifact
from dscops.domain.model import Database, EnvValue, InfraModel, Service


class ComposeBackend:
    name = "compose"
    description = "Docker Compose (compose.yaml)"

    def generate(self, model: InfraModel) -> list[Artifact]:
        services: dict[str, Any] = {}
        volumes: dict[str, Any] = {}
        links_by_source: dict[str, list[str]] = {}
        for link in model.links:
            links_by_source.setdefault(link.source, []).append(link.target)

        database_names = {database.name for database in model.databases}
        for service in model.services:
            services[service.name] = _service_definition(
                service,
                links_by_source.get(service.name, []),
                database_names,
            )
        for database in model.databases:
            services[database.name] = _database_definition(database)
            volumes[f"{database.name}_data"] = {"name": f"dscops_{database.name}_data"}

        document: dict[str, Any] = {"services": services}
        if volumes:
            document["volumes"] = volumes
        return [Artifact(path="compose.yaml", content=dump_yaml(document))]


def _service_definition(
    service: Service,
    link_targets: list[str],
    database_names: set[str],
) -> dict[str, Any]:
    definition: dict[str, Any] = {
        "image": service.image,
        "restart": "unless-stopped",
        "user": service.user or DEFAULT_CONTAINER_USER,
        "security_opt": ["no-new-privileges:true"],
        "init": True,
        "environment": _environment(service),
    }
    if service.command:
        definition["command"] = ["sh", "-c", service.command]
    if service.port is not None:
        if service.public:
            definition["ports"] = [_published_port(service.port, service.replicas)]
        else:
            definition["expose"] = [str(service.port)]

    deploy: dict[str, Any] = {"replicas": service.replicas}
    limits = _limits(service)
    if limits:
        deploy["resources"] = {"limits": limits}
    definition["deploy"] = deploy

    depends_on = _depends_on(link_targets, database_names, service.name)
    if depends_on:
        definition["depends_on"] = depends_on

    definition["labels"] = {"dscops.resource": "service", "dscops.name": service.name}
    return definition


def _database_definition(database: Database) -> dict[str, Any]:
    port = database_port(database)
    definition: dict[str, Any] = {
        "image": database_image(database),
        "restart": "unless-stopped",
        "security_opt": ["no-new-privileges:true"],
        "environment": _database_environment(database),
        "volumes": [f"{database.name}_data:{database_data_path(database)}"],
        "expose": [str(port)],
        "deploy": {"replicas": 1},
        "labels": {
            "dscops.resource": "database",
            "dscops.name": database.name,
            "dscops.size": database.size or "unbounded",
        },
    }
    if database.public:
        definition["ports"] = [f"{port}:{port}"]
    if database.engine == "redis":
        definition["command"] = [
            "sh",
            "-c",
            'exec redis-server --requirepass "$$REDIS_PASSWORD"',
        ]
    healthcheck = _database_healthcheck(database)
    if healthcheck:
        definition["healthcheck"] = healthcheck
    return definition


def _environment(service: Service) -> dict[str, str]:
    environment: dict[str, str] = {}
    for key, value in service.env.items():
        environment[key] = _env_value(value)
    return environment


def _env_value(value: EnvValue) -> str:
    if value.secret:
        return "${" + sanitize_variable(value.value) + "}"
    return value.value


def _database_environment(database: Database) -> dict[str, str]:
    password = "${" + database_password_variable(database) + "}"
    engine = database.engine
    if engine in {"postgres", "postgresql"}:
        return {
            "POSTGRES_USER": database.name,
            "POSTGRES_PASSWORD": password,
            "POSTGRES_DB": database.name,
        }
    if engine in {"mysql", "mariadb"}:
        return {
            "MYSQL_ROOT_PASSWORD": password,
            "MYSQL_DATABASE": database.name,
        }
    if engine in {"mongodb", "mongo"}:
        return {
            "MONGO_INITDB_ROOT_USERNAME": database.name,
            "MONGO_INITDB_ROOT_PASSWORD": password,
            "MONGO_INITDB_DATABASE": database.name,
        }
    if engine == "redis":
        return {
            "REDIS_PASSWORD": password,
        }
    return {}


def _database_healthcheck(database: Database) -> dict[str, Any] | None:
    engine = database.engine
    password = "${" + database_password_variable(database) + "}"
    if engine in {"postgres", "postgresql"}:
        return {
            "test": ["CMD-SHELL", f"pg_isready -U {database.name} -d {database.name}"],
            "interval": "5s",
            "timeout": "3s",
            "retries": 10,
        }
    if engine in {"mysql", "mariadb"}:
        return {
            "test": ["CMD-SHELL", "mysqladmin ping -h 127.0.0.1 --silent"],
            "interval": "5s",
            "timeout": "3s",
            "retries": 10,
        }
    if engine in {"mongodb", "mongo"}:
        return {
            "test": [
                "CMD-SHELL",
                (
                    "mongosh --quiet --username "
                    f"{database.name} --password {password} --authenticationDatabase admin "
                    "--eval 'db.adminCommand({ping:1}).ok'"
                ),
            ],
            "interval": "10s",
            "timeout": "5s",
            "retries": 10,
        }
    if engine == "redis":
        return {
            "test": ["CMD-SHELL", 'redis-cli -a "$$REDIS_PASSWORD" ping'],
            "interval": "5s",
            "timeout": "3s",
            "retries": 10,
        }
    return None


def _depends_on(
    targets: list[str],
    database_names: set[str],
    self_name: str,
) -> dict[str, dict[str, str]]:
    dependencies: dict[str, dict[str, str]] = {}
    for target in targets:
        if target == self_name or target in dependencies:
            continue
        condition = "service_healthy" if target in database_names else "service_started"
        dependencies[target] = {"condition": condition}
    return dependencies


def _published_port(port: int, replicas: int) -> str:
    if replicas <= 1:
        return f"{port}:{port}"
    return f"{port}-{port + replicas - 1}:{port}"


def _limits(service: Service) -> dict[str, str]:
    if service.resources is None:
        return {}
    limits: dict[str, str] = {}
    if service.resources.cpu:
        limits["cpus"] = _compose_cpu(service.resources.cpu)
    if service.resources.memory:
        limits["memory"] = _compose_memory(service.resources.memory)
    return limits


def _compose_cpu(value: str) -> str:
    match = re.fullmatch(r"\s*(\d+)m\s*", value)
    if match is None:
        return value.strip()
    return f"{int(match.group(1)) / 1000:.3f}".rstrip("0").rstrip(".")


def _compose_memory(value: str) -> str:
    normalized = value.strip()
    replacements = {"Ki": "K", "Mi": "M", "Gi": "G", "Ti": "T"}
    for suffix, replacement in replacements.items():
        if normalized.endswith(suffix):
            return normalized[: -len(suffix)] + replacement
    return normalized
