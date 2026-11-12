"""Kubernetes backend: Deployments, Services, Ingress and StatefulSets."""

from __future__ import annotations

from typing import Any

from dscops.backends._common import (
    database_data_path,
    database_image,
    database_password_variable,
    database_port,
    database_secret_name,
    numeric_uid,
    service_secret_name,
)
from dscops.backends._yaml import dump_yaml_documents
from dscops.backends.base import Artifact
from dscops.domain.model import Database, InfraModel, Service
from dscops.shared.values import normalize_storage_size

_APP_LABEL = "app"
_MANAGED_BY = "app.kubernetes.io/managed-by"


class KubernetesBackend:
    name = "kubernetes"
    description = "Kubernetes manifests (Deployment/Service/Ingress/StatefulSet)"

    def generate(self, model: InfraModel) -> list[Artifact]:
        documents: list[dict[str, Any]] = []
        for service in model.services:
            documents.append(_deployment(service))
            if service.port is not None:
                documents.append(_service(service))
                if service.public:
                    documents.append(_ingress(service))
        for database in model.databases:
            documents.append(_statefulset(database))
            documents.append(_database_service(database))
        return [Artifact(path="k8s.yaml", content=dump_yaml_documents(documents))]


def _labels(name: str, kind: str) -> dict[str, str]:
    return {
        _APP_LABEL: name,
        "dscops.io/kind": kind,
        _MANAGED_BY: "dscops",
    }


def _metadata(name: str, kind: str) -> dict[str, Any]:
    return {"name": name, "labels": _labels(name, kind)}


def _security_context(user: str | None) -> tuple[dict[str, Any], dict[str, Any]]:
    uid = numeric_uid(user)
    normalized_user = user.strip().lower() if user is not None else None
    is_root = normalized_user is not None and (
        uid == 0 or normalized_user == "root" or normalized_user.startswith("root:")
    )
    pod: dict[str, Any] = {"runAsNonRoot": not is_root}
    if uid is not None:
        pod["runAsUser"] = uid
    elif user is None:
        pod["runAsUser"] = 10001
    if user is not None and ":" in user:
        gid = numeric_uid(user.split(":", 1)[1])
        if gid is not None:
            pod["runAsGroup"] = gid
            pod["fsGroup"] = gid
    container: dict[str, Any] = {
        "allowPrivilegeEscalation": False,
        "capabilities": {"drop": ["ALL"]},
    }
    return pod, container


def _env(service: Service) -> list[dict[str, Any]]:
    env: list[dict[str, Any]] = []
    for key, value in service.env.items():
        if value.secret:
            env.append(
                {
                    "name": key,
                    "valueFrom": {
                        "secretKeyRef": {
                            "name": service_secret_name(service.name),
                            "key": key,
                        }
                    },
                }
            )
        else:
            env.append({"name": key, "value": value.value})
    return env


def _resources(service: Service) -> dict[str, Any] | None:
    if service.resources is None:
        return None
    limits: dict[str, str] = {}
    if service.resources.cpu:
        limits["cpu"] = service.resources.cpu
    if service.resources.memory:
        limits["memory"] = service.resources.memory
    return {"limits": limits} if limits else None


def _deployment(service: Service) -> dict[str, Any]:
    pod_security, container_security = _security_context(service.user)
    container: dict[str, Any] = {
        "name": service.name,
        "image": service.image,
        "imagePullPolicy": "IfNotPresent",
        "securityContext": container_security,
    }
    if service.command:
        container["command"] = ["sh", "-c"]
        container["args"] = [service.command]
    if service.port is not None:
        container["ports"] = [{"name": "http", "containerPort": service.port, "protocol": "TCP"}]
    if service.env:
        container["env"] = _env(service)
    resources = _resources(service)
    if resources is not None:
        container["resources"] = resources
    return {
        "apiVersion": "apps/v1",
        "kind": "Deployment",
        "metadata": _metadata(service.name, "service"),
        "spec": {
            "replicas": service.replicas,
            "selector": {"matchLabels": {_APP_LABEL: service.name}},
            "template": {
                "metadata": {"labels": _labels(service.name, "service")},
                "spec": {
                    "securityContext": pod_security,
                    "containers": [container],
                },
            },
        },
    }


def _require_port(service: Service) -> int:
    """Ports are optional on the model, but a Service or Ingress always needs one."""

    if service.port is None:
        raise RuntimeError(f"el servicio '{service.name}' no tiene puerto")
    return service.port


def _service(service: Service) -> dict[str, Any]:
    port = _require_port(service)
    return {
        "apiVersion": "v1",
        "kind": "Service",
        "metadata": _metadata(service.name, "service"),
        "spec": {
            "type": "ClusterIP",
            "selector": {_APP_LABEL: service.name},
            "ports": [
                {
                    "name": "http",
                    "port": port,
                    "targetPort": port,
                    "protocol": "TCP",
                }
            ],
        },
    }


def _ingress(service: Service) -> dict[str, Any]:
    port = _require_port(service)
    return {
        "apiVersion": "networking.k8s.io/v1",
        "kind": "Ingress",
        "metadata": _metadata(service.name, "service"),
        "spec": {
            "rules": [
                {
                    "host": f"{service.name}.dscops.local",
                    "http": {
                        "paths": [
                            {
                                "path": "/",
                                "pathType": "Prefix",
                                "backend": {
                                    "service": {
                                        "name": service.name,
                                        "port": {"number": port},
                                    }
                                },
                            }
                        ]
                    },
                }
            ]
        },
    }


def _database_env(database: Database) -> list[dict[str, Any]]:
    secret_name = database_secret_name(database)

    def secret_ref(env_name: str, key: str) -> dict[str, Any]:
        return {
            "name": env_name,
            "valueFrom": {"secretKeyRef": {"name": secret_name, "key": key}},
        }

    if database.engine in {"postgres", "postgresql"}:
        return [
            {"name": "POSTGRES_USER", "value": database.name},
            secret_ref("POSTGRES_PASSWORD", "POSTGRES_PASSWORD"),
            {"name": "POSTGRES_DB", "value": database.name},
        ]
    if database.engine in {"mysql", "mariadb"}:
        return [
            secret_ref("MYSQL_ROOT_PASSWORD", "MYSQL_ROOT_PASSWORD"),
            {"name": "MYSQL_DATABASE", "value": database.name},
        ]
    if database.engine in {"mongodb", "mongo"}:
        return [
            {"name": "MONGO_INITDB_ROOT_USERNAME", "value": database.name},
            secret_ref("MONGO_INITDB_ROOT_PASSWORD", "MONGO_INITDB_ROOT_PASSWORD"),
            {"name": "MONGO_INITDB_DATABASE", "value": database.name},
        ]
    if database.engine == "redis":
        return [secret_ref("REDIS_PASSWORD", database_password_variable(database))]
    return []


def _statefulset(database: Database) -> dict[str, Any]:
    port = database_port(database)
    container: dict[str, Any] = {
        "name": database.name,
        "image": database_image(database),
        "imagePullPolicy": "IfNotPresent",
        "ports": [{"name": "db", "containerPort": port, "protocol": "TCP"}],
        "volumeMounts": [{"name": "data", "mountPath": database_data_path(database)}],
        "env": _database_env(database),
        "securityContext": {
            "allowPrivilegeEscalation": False,
            "capabilities": {"drop": ["ALL"]},
        },
    }
    if database.engine == "redis":
        container["args"] = ["--requirepass", "$(REDIS_PASSWORD)"]
    return {
        "apiVersion": "apps/v1",
        "kind": "StatefulSet",
        "metadata": _metadata(database.name, "database"),
        "spec": {
            "serviceName": database.name,
            "replicas": 1,
            "selector": {"matchLabels": {_APP_LABEL: database.name}},
            "template": {
                "metadata": {"labels": _labels(database.name, "database")},
                "spec": {
                    "securityContext": {"fsGroup": 999},
                    "containers": [container],
                },
            },
            "volumeClaimTemplates": [
                {
                    "metadata": {"name": "data"},
                    "spec": {
                        "accessModes": ["ReadWriteOnce"],
                        "resources": {
                            "requests": {"storage": normalize_storage_size(database.size)}
                        },
                    },
                }
            ],
        },
    }


def _database_service(database: Database) -> dict[str, Any]:
    port = database_port(database)
    service_type = "LoadBalancer" if database.public else "ClusterIP"
    return {
        "apiVersion": "v1",
        "kind": "Service",
        "metadata": _metadata(database.name, "database"),
        "spec": {
            "type": service_type,
            "selector": {_APP_LABEL: database.name},
            "ports": [
                {
                    "name": "db",
                    "port": port,
                    "targetPort": port,
                    "protocol": "TCP",
                }
            ],
        },
    }
