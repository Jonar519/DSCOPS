"""Shared helper tests."""

from __future__ import annotations

import pytest

from dscops.backends._common import (
    database_image,
    database_port,
    numeric_uid,
    sanitize_variable,
    terraform_identifier,
)
from dscops.domain.model import Database
from dscops.shared.values import (
    env_text,
    image_tag,
    is_pinned_image,
    is_sensitive_env_key,
    normalize_storage_size,
)


@pytest.mark.parametrize(
    ("key", "sensitive"),
    [
        ("DB_PASSWORD", True),
        ("STRIPE_API_KEY", True),
        ("GITHUB_TOKEN", True),
        ("SSH_KEY", True),
        ("DATABASE_URL", True),
        ("APP_MODE", False),
        ("DEBUG", False),
    ],
)
def test_sensitive_env_keys(key: str, sensitive: bool) -> None:
    assert is_sensitive_env_key(key) is sensitive


@pytest.mark.parametrize(
    ("image", "tag"),
    [
        ("python:3.12-slim", "3.12-slim"),
        ("python", None),
        ("localhost:5000/app:1.0", "1.0"),
        ("repo/app@sha256:abc", "sha256:abc"),
        ("", None),
    ],
)
def test_image_tag(image: str, tag: str | None) -> None:
    assert image_tag(image) == tag


def test_is_pinned_image() -> None:
    assert is_pinned_image("python:3.12-slim") is True
    assert is_pinned_image("python:latest") is False
    assert is_pinned_image("python") is False
    assert is_pinned_image("repo/app@sha256:abc") is True


@pytest.mark.parametrize(
    ("size", "expected"),
    [
        (None, "1Gi"),
        ("20GB", "20Gi"),
        ("512Mi", "512Mi"),
        ("1.5GB", "1.5Gi"),
        ("500MB", "500Mi"),
        ("100", "100Gi"),
        ("custom", "custom"),
    ],
)
def test_normalize_storage_size(size: str | None, expected: str) -> None:
    assert normalize_storage_size(size) == expected


def test_env_text() -> None:
    assert env_text(True) == "true"
    assert env_text(False) == "false"
    assert env_text(3) == "3"
    assert env_text("x") == "x"


def test_sanitize_variable() -> None:
    assert sanitize_variable("db-url") == "DB_URL"
    assert sanitize_variable("1password") == "DSCOPS_1PASSWORD"
    assert sanitize_variable("") == "DSCOPS_"


def test_terraform_identifier() -> None:
    assert terraform_identifier("api-v2") == "api_v2"
    assert terraform_identifier("2api") == "dscops_2api"


def test_database_conventions() -> None:
    database = Database(name="main", engine="postgres")
    assert database_image(database) == "postgres:16"
    assert database_port(database) == 5432
    assert database_image(Database(name="db", engine="custom")) == "custom:latest"
    assert database_port(Database(name="db", engine="custom", port=9000)) == 9000


def test_numeric_uid() -> None:
    assert numeric_uid("1000:1000") == 1000
    assert numeric_uid("1000") == 1000
    assert numeric_uid("app") is None
    assert numeric_uid(None) is None
