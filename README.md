# DSCOPS

> **Declarative Secure Compiler for Ops.** Escribe tu infraestructura una vez,
> compílala segura.

[![CI](https://github.com/Jonar519/DSCOPS/actions/workflows/ci.yml/badge.svg)](https://github.com/Jonar519/DSCOPS/actions/workflows/ci.yml)
[![Python 3.12+](https://img.shields.io/badge/python-3.12%2B-3776ab.svg)](https://www.python.org/)
[![License: MIT](https://img.shields.io/badge/license-MIT-green.svg)](LICENSE)
[![Coverage: 80%+](https://img.shields.io/badge/coverage-80%25%2B-brightgreen.svg)](tests/)

DSCOPS es un compilador de un lenguaje declarativo propio (`.dscops`) que
describe servicios, bases de datos y sus dependencias. El compilador valida la
sintaxis, construye un modelo neutral, ejecuta **10 reglas de seguridad** y
genera artefactos reales para Docker Compose, Kubernetes, GitHub Actions y
Terraform.

No es un framework: es un compilador completo con lexer, parser LALR, AST,
análisis semántico, IR, análisis estático y backends. Se usa por CLI o por API
REST, y ambas interfaces comparten exactamente la misma lógica.

```text
.dscops -> [Frontend] -> AST -> [Semántica] -> IR -> [Seguridad] -> hallazgos
                                                |
                                                +-> [Backends] -> compose / k8s / CI / HCL
```

## Demo rápida

```bash
uv sync --extra dev
uv run dscops check examples/app.dscops
uv run dscops build examples/app.dscops --target compose,kubernetes --out out
```

Salida de un archivo con defectos (`examples/invalid/insecure.dscops`):

```text
error[SEC001]: secreto hardcodeado en 'DB_PASSWORD' del servicio 'api'
  --> examples/invalid/insecure.dscops:6:23
   |
 6 |   env: { DB_PASSWORD: "admin123", DEBUG: true }
   |                       ^^^^^^^^^^
   = ayuda: usa DB_PASSWORD: secret("db_password") en lugar de un valor literal

error[SEC003]: la base de datos 'main' está expuesta públicamente
  --> examples/invalid/insecure.dscops:10:1
    |
 10 | database main {
    | ^
    = ayuda: usa expose: private; las bases de datos no deben ser accesibles desde internet

Resumen: 3 error(es), 4 advertencia(s), 2 aviso(s)
```

El CLI devuelve código de salida distinto de cero cuando hay errores, así que
sirve directamente como *gate* de CI.

![Playground de DSCOPS](docs/playground.png)

El playground se sirve desde la misma API (`/playground`) y llama a los mismos
endpoints que un cliente externo.

## Características

- Lenguaje pequeño y legible: `service`, `database`, propiedades y `->`.
- Parser LALR con Lark y errores con línea, columna y sugerencia.
- AST separado del **IR neutral**; los backends no conocen el lenguaje.
- 10 reglas de seguridad con severidad, mensaje y ayuda accionable.
- Docker Compose, Kubernetes, GitHub Actions y Terraform.
- API FastAPI versionada con OpenAPI en `/docs`.
- Playground web sin build de frontend en `/playground`.
- CLI Typer + Rich con salida estilo Rust.
- 160+ pruebas, snapshots, cobertura > 80 %, Ruff, mypy estricto, pre-commit.
- Dockerfile non-root y CI que valida sus propios ejemplos y artefactos.

## Instalación

Requisitos: Python 3.12+.

Con [uv](https://docs.astral.sh/uv/) (recomendado):

```bash
uv sync --extra dev
uv run dscops --version
```

Con `pip`:

```bash
python -m venv .venv
# Windows: .venv\Scripts\activate
source .venv/bin/activate
pip install -e ".[dev]"
dscops --version
```

## CLI

```bash
dscops check app.dscops                  # sintaxis + semántica + seguridad
dscops check app.dscops --strict         # también falla con warnings/avisos
dscops check examples/*.dscops           # varios archivos
dscops build app.dscops -t compose,k8s -o out
dscops build app.dscops -t github -t terraform -o out
dscops targets
dscops serve                             # API + playground en :8000
```

`--target` acepta alias: `compose`/`docker`, `kubernetes`/`k8s`,
`github-actions`/`github`/`gha`, `terraform`/`tf`.

Artefactos generados:

| Target | Archivo |
|---|---|
| `compose` | `compose.yaml` |
| `kubernetes` | `k8s.yaml` (multi-documento) |
| `github-actions` | `.github/workflows/dscops.yml` |
| `terraform` | `terraform/main.tf` |

## API REST

```bash
uv run dscops serve
# http://127.0.0.1:8000/docs
# http://127.0.0.1:8000/playground
```

| Método | Ruta | Cuerpo | Respuesta |
|---|---|---|---|
| GET | `/health` | — | `{status, version}` |
| GET | `/v1/targets` | — | lista de backends y alias |
| POST | `/v1/check` | `{source}` | `{ok, diagnostics[]}` |
| POST | `/v1/compile` | `{source, targets[]}` | `{ok, diagnostics[], artifacts[], targets[]}` |

```bash
curl -s http://127.0.0.1:8000/v1/compile \
  -H 'Content-Type: application/json' \
  -d '{"source":"service api { image: \"python:3.12-slim\" port: 8000 }","targets":["compose"]}'
```

Reglas de la API:

- Código inválido responde **200** con `ok: false` y diagnósticos.
- Cuerpo inválido, campos extra o más de 100 000 caracteres responden **422**.
- No hay estado ni escritura de archivos en el servidor.
- `POST /compile` no genera artefactos si hay cualquier error.

## El lenguaje

```text
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

database main {
  engine: postgres
  version: "16"
  size: "20GB"
  expose: private
}

api -> main
```

### Propiedades de `service`

| Propiedad | Tipo | Obligatoria | Descripción |
|---|---|---|---|
| `image` | string | sí | Imagen del contenedor. Fija tag o digest. |
| `port` | número | no | Puerto del contenedor (1–65535). |
| `replicas` | número | no | Réplicas deseadas, por defecto `1`. |
| `env` | objeto | no | Variables; usa `secret("...")` para secretos. |
| `expose` | `public`/`private` | no | Por defecto `private`. |
| `user` | string | no | `uid[:gid]`; si falta, SEC006 advierte. |
| `resources` | objeto | no | `{ cpu, memory }` para límites. |
| `command` | string | no | Comando de arranque (`sh -c`). |

### Propiedades de `database`

| Propiedad | Tipo | Obligatoria | Descripción |
|---|---|---|---|
| `engine` | identificador | sí | `postgres`, `mysql`, `mariadb`, `mongodb`, `redis` o custom. |
| `version` | escalar | no | Tag de la imagen; si falta se usa una versión estable. |
| `size` | string | no | Tamaño de volumen; se convierte a cantidad de Kubernetes. |
| `expose` | `public`/`private` | no | Por defecto `private`; `public` dispara SEC003. |
| `port` | número | no | Puerto de la base de datos. |

### Valores

- `STRING`: `"texto"`.
- `NUMBER`: entero positivo.
- `BOOL`: `true` / `false`.
- `NAME`: identificador, por ejemplo `postgres` o `public`.
- `call`: `secret("db_url")`.
- `object`: `{ CLAVE: valor, ... }`.

`secret("nombre")` **no** contiene el secreto: es una referencia. Compose usa
`${NOMBRE}` y Kubernetes usa `secretKeyRef`; el valor se inyecta en tiempo de
despliegue.

### Semántica

- Nombres únicos entre servicios y bases de datos (`SEC009`).
- Las dependencias deben referenciar recursos existentes (`SEC008`).
- `image` y `engine` son obligatorios.
- `port`, `replicas`, `expose`, `env`, `resources`, `command` y `user` se validan
  por tipo y por rango.
- Las referencias hacia adelante son válidas: puedes escribir el `->` antes de
  la declaración.

Gramática completa: [`src/dscops/frontend/grammar.lark`](src/dscops/frontend/grammar.lark).
Referencia detallada: [`docs/language.md`](docs/language.md).

## Reglas de seguridad

| Código | Regla | Severidad |
|---|---|---|
| `SEC001` | Secreto hardcodeado en una variable sensible (`PASSWORD`, `TOKEN`, `KEY`, etc.). | ERROR |
| `SEC002` | Imagen con `latest` o sin tag. | WARNING |
| `SEC003` | Base de datos expuesta públicamente. | ERROR |
| `SEC004` | Servicio público sin puerto o con puerto sensible (22, 3306, 5432, 6379, 27017). | WARNING |
| `SEC005` | Servicio público con una sola réplica. | INFO |
| `SEC006` | Contenedor sin `user` o corriendo como root. | WARNING |
| `SEC007` | Faltan límites de CPU o memoria. | INFO |
| `SEC008` | Dependencia hacia un recurso inexistente (semántica). | ERROR |
| `SEC009` | Recurso duplicado (semántica). | ERROR |
| `SEC010` | `DEBUG: true` en un servicio público. | WARNING |

Detalle de cada regla, ejemplos y mitigación: [`docs/rules.md`](docs/rules.md).

## Arquitectura

```mermaid
flowchart LR
  SRC[".dscops"] --> FE["frontend<br/>Lark"]
  FE --> AST["domain.ast"]
  AST --> SEM["semantic<br/>resolver"]
  SEM --> IR["domain.model<br/>IR neutral"]
  IR --> AN["analysis<br/>8 reglas"]
  IR --> BE["backends"]
  AN --> DIAG["Diagnostic"]
  BE --> ART["Artifact"]
  DIAG --> APP["app"]
  ART --> APP
  APP --> CLI["Typer CLI"]
  APP --> API["FastAPI"]
```

Regla de dependencias:

```text
interfaces -> app -> frontend / semantic / analysis / backends -> domain
```

- `domain/` es el contrato congelado: AST, IR y diagnósticos, solo stdlib.
- `app/` es la única lógica compartida por CLI y API.
- Un backend nuevo no toca el parser, la semántica ni las reglas.
- Una regla nueva no toca los backends ni las interfaces.
- Igual que en un compilador clásico, el IR permite que el frontend y los
  backends evolucionen por separado.

Más detalle: [`docs/architecture.md`](docs/architecture.md).

## Cómo agregar una regla

1. Crea `src/dscops/analysis/rules/sec011_mi_regla.py`.
2. Implementa el protocolo `Rule` (`code`, `check(model) -> list[Diagnostic]`).
3. Regístrala en `RULES` de `analysis/engine.py`.
4. Añade dos pruebas: un caso que la dispara y uno que no.
5. No toques `app/`, `domain/` ni los backends.

## Cómo agregar un backend

1. Crea `src/dscops/backends/mi_backend.py`.
2. Implementa `name`, `description` y `generate(model) -> list[Artifact]`.
3. Genera YAML/JSON desde `dict`; usa Jinja2 solo para formatos de texto.
4. Regístralo en `backends/__init__.py` y prueba su snapshot.
5. El CLI y la API lo verán automáticamente con `dscops targets`.

## Calidad

```bash
ruff check .
ruff format --check .
mypy src
pytest --cov=dscops --cov-fail-under=80
dscops check examples/*.dscops
```

El CI ejecuta además:

- `docker compose -f dist/compose.yaml config` sobre el Compose generado.
- `kubeconform -strict` sobre el Kubernetes generado.
- `docker build` de la API y un escaneo Trivy de la imagen.
- Semgrep con las reglas OWASP Top 10, Bandit, pip-audit, gitleaks y Trivy sobre el repo.
- SonarQube, cuando existen los secrets `SONAR_TOKEN` y `SONAR_HOST_URL`.

Pruebas incluidas:

- Frontend válido, inválido, comentarios, objetos anidados y errores bonitos.
- Un caso por chequeo semántico.
- Dos casos por regla de seguridad.
- Snapshots de Compose y Kubernetes.
- CLI con códigos de salida y escritura de artefactos.
- API con casos felices, 422 y errores de usuario.
- End-to-end sobre todos los ejemplos.

## Docker

```bash
docker build -t dscops-api .
docker run --rm -p 8000:8000 dscops-api
# http://127.0.0.1:8000/playground
```

La imagen usa `python:3.12-slim`, corre con UID 10001 y tiene `HEALTHCHECK`
contra `/health`. DSCOPS pasa su propia regla SEC006.

## Demo de 5 minutos

1. Muestra `examples/invalid/insecure.dscops`:

   ```bash
   dscops check examples/invalid/insecure.dscops
   ```

   Se ven `SEC001`, `SEC002`, `SEC003`, `SEC004`, `SEC005`, `SEC006`, `SEC007`
   y `SEC010`, además de la dependencia rota `SEC008`.

2. Corrige el archivo o abre `examples/app.dscops`:

   ```bash
   dscops check examples/app.dscops
   dscops build examples/app.dscops --target compose,kubernetes --out out
   ```

3. Levanta el resultado:

   ```bash
   cd out
   DB_URL='postgresql://main:change-me@main:5432/main' \
   MAIN_PASSWORD='change-me' \
   CACHE_PASSWORD='change-me' \
   docker compose up
   ```

   Abre `http://localhost:8000`; las tres réplicas de `api` se publican en
   `8000-8002`. La base de datos `main` y `cache` quedan en la red interna.

4. Muestra la API:

   ```bash
   dscops serve
   ```

   Abre `/playground`, pulsa **Validar** y luego **Compilar**. También puedes
   probar `/docs`.

## Estructura

```text
dscops/
├─ pyproject.toml
├─ AGENTS.md
├─ Dockerfile
├─ examples/
│  ├─ app.dscops
│  ├─ minimal.dscops
│  └─ invalid/
├─ docs/
├─ tests/
│  ├─ unit/
│  └─ integration/
└─ src/dscops/
   ├─ domain/       # AST, IR, Diagnostic (stdlib puro)
   ├─ frontend/     # grammar.lark + parser
   ├─ semantic/     # AST -> IR
   ├─ analysis/     # motor + 8 reglas
   ├─ backends/     # compose, kubernetes, github_actions, terraform
   ├─ app/          # check_source / compile_source
   ├─ shared/       # helpers puros
   └─ interfaces/   # CLI Typer y API FastAPI
```

## Decisiones y límites

- **LALR**: la gramática es deliberadamente pequeña y sin ambigüedad. Cambiar a
  ANTLR o Flex/Bison solo afecta a `frontend/`.
- **IR neutral**: el parser no sabe qué es Docker; los backends no saben qué es
  un `service` del DSL.
- **YAML desde dicts**: evita errores de indentación y permite probar la
  estructura antes de serializar.
- **Secretos por referencia**: el compilador nunca resuelve ni imprime valores.
- **Terraform** usa el provider Docker para que el artefacto sea ejecutable sin
  un clúster; el foco principal son Compose y Kubernetes.
- **Kubernetes** genera `Secret` por referencia, no los valores. Créalos con
  `kubectl create secret` antes de aplicar.
- Fuera de alcance: base de datos propia, autenticación, microservicios,
  despliegue real, LSP completo y optimizadores.

## Definition of Done

- [x] `dscops check` y `dscops build` funcionan con los ejemplos.
- [x] 8 reglas de análisis + 2 chequeos semánticos, con pruebas.
- [x] Compose y Kubernetes generan archivos válidos (CI los valida).
- [x] API `/health`, `/v1/targets`, `/v1/check`, `/v1/compile` y `/docs`.
- [x] Cobertura >= 80 % y CI en verde.
- [x] README, diagrama, ejemplos y guía para extender.
- [x] Playground web, GitHub Actions y Terraform como extras.

## Equipo

Proyecto de Compiladores — Séptimo Semestre. Hecho para demostrar que un
compilador puede resolver un problema real de Backend/Cloud/DevSecOps sin
sobreingeniería.

> **Mantra:** simple, modular, probado y entendido.
