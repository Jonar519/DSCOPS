"""Shared fixtures and canonical source snippets."""

from __future__ import annotations

import pytest
from typer.testing import CliRunner

from dscops.domain.model import InfraModel
from dscops.frontend import parse
from dscops.semantic import build_model

VALID_SOURCE = """\
# A complete, secure example used across the test suite.
service api {
  image: "python:3.12-slim"
  port: 8000
  replicas: 3
  env: { DB_URL: secret("db_url"), DEBUG: false }
  expose: public
  user: "10001:10001"
  resources: { cpu: "500m", memory: "512Mi" }
  command: "python -m http.server 8000"
}

service worker {
  image: "python:3.12-slim"
  replicas: 2
  env: { DB_URL: secret("db_url") }
  expose: private
  user: "10001:10001"
  resources: { cpu: "250m", memory: "256Mi" }
}

database main {
  engine: postgres
  version: "16"
  size: "20GB"
  expose: private
}

database cache {
  engine: redis
  version: "7.2"
  size: "5GB"
  expose: private
}

api -> main
api -> cache
worker -> main
"""

INSECURE_SOURCE = """\
service api {
  image: "python:latest"
  port: 22
  replicas: 1
  env: { DB_PASSWORD: "admin123", DEBUG: true }
  expose: public
}

database main {
  engine: postgres
  version: "16"
  expose: public
}

api -> ghost
"""


@pytest.fixture
def valid_source() -> str:
    return VALID_SOURCE


@pytest.fixture
def insecure_source() -> str:
    return INSECURE_SOURCE


@pytest.fixture
def model() -> InfraModel:
    return build_model(parse(VALID_SOURCE)).model


@pytest.fixture
def runner() -> CliRunner:
    return CliRunner()
