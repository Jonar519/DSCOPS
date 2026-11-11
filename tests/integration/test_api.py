"""HTTP API tests using FastAPI's TestClient."""

from __future__ import annotations

from collections.abc import Iterator

import pytest
from fastapi.testclient import TestClient

from dscops.app import MAX_SOURCE_LENGTH
from dscops.interfaces.api.app import app


@pytest.fixture
def client() -> Iterator[TestClient]:
    with TestClient(app) as test_client:
        yield test_client


def test_health(client: TestClient) -> None:
    response = client.get("/health")
    assert response.status_code == 200
    assert response.json() == {"status": "ok", "version": "0.1.0"}
    assert client.get("/v1/health").json() == {"status": "ok", "version": "0.1.0"}


def test_targets(client: TestClient) -> None:
    response = client.get("/v1/targets")
    assert response.status_code == 200
    data = response.json()
    assert [item["name"] for item in data] == [
        "compose",
        "kubernetes",
        "github-actions",
        "terraform",
    ]
    assert data[1]["aliases"] == ["k8s"]


def test_check_valid(client: TestClient, valid_source: str) -> None:
    response = client.post("/v1/check", json={"source": valid_source})
    assert response.status_code == 200
    data = response.json()
    assert data == {"ok": True, "diagnostics": []}


def test_check_invalid(client: TestClient, insecure_source: str) -> None:
    response = client.post("/v1/check", json={"source": insecure_source})
    assert response.status_code == 200
    data = response.json()
    assert data["ok"] is False
    assert any(item["code"] == "SEC001" for item in data["diagnostics"])
    assert any(item["severity"] == "error" for item in data["diagnostics"])


def test_check_syntax_error(client: TestClient) -> None:
    response = client.post("/v1/check", json={"source": "service api {"})
    assert response.status_code == 200
    data = response.json()
    assert data["ok"] is False
    assert data["diagnostics"][0]["code"] == "SYN001"
    assert data["diagnostics"][0]["line"] == 1


def test_compile(client: TestClient, valid_source: str) -> None:
    response = client.post(
        "/v1/compile",
        json={"source": valid_source, "targets": ["compose", "k8s"]},
    )
    assert response.status_code == 200
    data = response.json()
    assert data["ok"] is True
    assert data["targets"] == ["compose", "kubernetes"]
    assert [artifact["path"] for artifact in data["artifacts"]] == [
        "compose.yaml",
        "k8s.yaml",
    ]
    assert "services:" in data["artifacts"][0]["content"]


def test_compile_with_errors_has_no_artifacts(client: TestClient, insecure_source: str) -> None:
    response = client.post("/v1/compile", json={"source": insecure_source, "targets": ["compose"]})
    assert response.status_code == 200
    data = response.json()
    assert data["ok"] is False
    assert data["artifacts"] == []
    assert data["targets"] == ["compose"]


def test_compile_unknown_target(client: TestClient, valid_source: str) -> None:
    response = client.post("/v1/compile", json={"source": valid_source, "targets": ["nope"]})
    assert response.status_code == 200
    data = response.json()
    assert data["ok"] is False
    assert data["targets"] == []
    assert data["diagnostics"][0]["code"] == "CFG002"


def test_compile_without_targets(client: TestClient, valid_source: str) -> None:
    response = client.post("/v1/compile", json={"source": valid_source, "targets": []})
    assert response.status_code == 200
    data = response.json()
    assert data["ok"] is False
    assert data["diagnostics"][0]["code"] == "CFG001"


def test_request_validation_errors(client: TestClient) -> None:
    assert client.post("/v1/check", json={}).status_code == 422
    assert client.post("/v1/check", json={"source": 1}).status_code == 422
    assert client.post("/v1/check", json={"source": "x", "extra": 1}).status_code == 422
    assert (
        client.post(
            "/v1/check",
            content="{",
            headers={"content-type": "application/json"},
        ).status_code
        == 422
    )


def test_source_size_limit(client: TestClient) -> None:
    response = client.post("/v1/check", json={"source": "x" * (MAX_SOURCE_LENGTH + 1)})
    assert response.status_code == 422


def test_playground_and_root(client: TestClient) -> None:
    page = client.get("/playground")
    assert page.status_code == 200
    assert page.headers["content-type"].startswith("text/html")
    assert "DSCOPS Playground" in page.text

    redirect = client.get("/", follow_redirects=False)
    assert redirect.status_code == 307
    assert redirect.headers["location"] == "/playground"
    assert client.get("/").status_code == 200


def test_openapi_docs(client: TestClient) -> None:
    assert client.get("/docs").status_code == 200
    schema = client.get("/openapi.json").json()
    assert schema["info"]["title"] == "DSCOPS API"
    assert "/v1/compile" in schema["paths"]
    assert "/v1/check" in schema["paths"]


def test_unversioned_compile_is_not_exposed(client: TestClient, valid_source: str) -> None:
    assert client.post("/compile", json={"source": valid_source, "targets": []}).status_code == 404
