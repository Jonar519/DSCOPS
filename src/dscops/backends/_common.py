"""Backend-independent conventions (databases, secret names, users)."""

from __future__ import annotations

import re

from dscops.domain.model import Database

DATABASE_IMAGES = {
    "postgres": "postgres",
    "postgresql": "postgres",
    "mysql": "mysql",
    "mariadb": "mariadb",
    "mongodb": "mongo",
    "mongo": "mongo",
    "redis": "redis",
}

DATABASE_DEFAULT_VERSIONS = {
    "postgres": "16",
    "postgresql": "16",
    "mysql": "8.4",
    "mariadb": "11",
    "mongodb": "7",
    "mongo": "7",
    "redis": "7.2",
}

DATABASE_PORTS = {
    "postgres": 5432,
    "postgresql": 5432,
    "mysql": 3306,
    "mariadb": 3306,
    "mongodb": 27017,
    "mongo": 27017,
    "redis": 6379,
}

DATABASE_DATA_PATHS = {
    "postgres": "/var/lib/postgresql/data",
    "postgresql": "/var/lib/postgresql/data",
    "mysql": "/var/lib/mysql",
    "mariadb": "/var/lib/mysql",
    "mongodb": "/data/db",
    "mongo": "/data/db",
    "redis": "/data",
}

DEFAULT_CONTAINER_USER = "10001:10001"


def sanitize_variable(name: str) -> str:
    """Turn a free-form name into an env-var/terraform-variable identifier."""

    normalized = re.sub(r"[^A-Za-z0-9_]", "_", name).upper()
    if not normalized or normalized[0].isdigit():
        normalized = f"DSCOPS_{normalized}"
    return normalized


def database_image(database: Database) -> str:
    base = DATABASE_IMAGES.get(database.engine, database.engine or "database")
    version = database.version or DATABASE_DEFAULT_VERSIONS.get(database.engine, "latest")
    return f"{base}:{version}"


def database_port(database: Database) -> int:
    if database.port is not None:
        return database.port
    return DATABASE_PORTS.get(database.engine, 5432)


def database_data_path(database: Database) -> str:
    return DATABASE_DATA_PATHS.get(database.engine, "/var/lib/data")


def database_password_variable(database: Database) -> str:
    return f"{sanitize_variable(database.name)}_PASSWORD"


def terraform_identifier(name: str) -> str:
    """Return a valid Terraform identifier (lowercase, starts with a letter)."""

    normalized = re.sub(r"[^a-z0-9_]", "_", name.lower())
    if not normalized or normalized[0].isdigit():
        normalized = f"dscops_{normalized}"
    return normalized


def database_secret_name(database: Database) -> str:
    return f"{database.name}-secrets"


def service_secret_name(service_name: str) -> str:
    return f"{service_name}-secrets"


def numeric_uid(user: str | None) -> int | None:
    """Extract the UID from a Docker-style ``uid[:gid]`` string."""

    if user is None:
        return None
    first = user.split(":", 1)[0].strip()
    if first.isdigit():
        return int(first)
    return None
