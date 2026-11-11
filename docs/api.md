# API REST

## Arranque

```bash
dscops serve --host 127.0.0.1 --port 8000
# o
uvicorn dscops.interfaces.api.app:app --reload
```

- OpenAPI/Swagger: <http://127.0.0.1:8000/docs>
- ReDoc: <http://127.0.0.1:8000/redoc>
- Playground: <http://127.0.0.1:8000/playground>
- Health: <http://127.0.0.1:8000/health>

## Endpoints

### `GET /health`

```json
{"status": "ok", "version": "0.1.0"}
```

### `GET /v1/targets`

```json
[
  {
    "name": "compose",
    "description": "Docker Compose (compose.yaml)",
    "aliases": ["docker", "docker-compose"]
  },
  {
    "name": "kubernetes",
    "description": "Kubernetes manifests (Deployment/Service/Ingress/StatefulSet)",
    "aliases": ["k8s"]
  }
]
```

### `POST /v1/check`

```bash
curl -s http://127.0.0.1:8000/v1/check \
  -H 'Content-Type: application/json' \
  -d '{"source":"service api { image: \"python:3.12-slim\" }"}'
```

```json
{
  "ok": true,
  "diagnostics": []
}
```

Un archivo inválido también responde **200**, con `ok: false`:

```json
{
  "ok": false,
  "diagnostics": [
    {
      "code": "SYN001",
      "severity": "error",
      "message": "token inesperado '}'",
      "line": 1,
      "column": 15,
      "length": 1,
      "hint": "se esperaba: una cadena, un número, true o false..."
    }
  ]
}
```

### `POST /v1/compile`

```bash
curl -s http://127.0.0.1:8000/v1/compile \
  -H 'Content-Type: application/json' \
  -d '{
    "source": "service api { image: \"python:3.12-slim\" port: 8000 }",
    "targets": ["compose", "k8s"]
  }'
```

```json
{
  "ok": true,
  "diagnostics": [],
  "targets": ["compose", "kubernetes"],
  "artifacts": [
    {"path": "compose.yaml", "content": "services:\n  api:\n..."},
    {"path": "k8s.yaml", "content": "apiVersion: apps/v1\n..."}
  ]
}
```

Si hay errores, `artifacts` es `[]` aunque algunos backends pudieran generar
contenido: la compilación es atómica.

## Reglas de error

| Situación | HTTP | Cuerpo |
|---|---|---|
| Código DSL inválido | 200 | `ok: false` + diagnósticos |
| Target desconocido | 200 | `ok: false` + `CFG002` |
| Sin targets | 200 | `ok: false` + `CFG001` |
| Fuente > 100 000 caracteres | 422 | error de validación |
| Falta `source` o tipo incorrecto | 422 | error de validación |
| Campo extra | 422 | error de validación |
| JSON malformado | 422 | error de validación |

La validación de la petición la hace Pydantic en el borde. Los schemas
(`interfaces/api/schemas.py`) no se filtran al dominio: se convierten a tipos
simples antes de llamar a `app`.

## Schemas

```python
class SourceRequest(BaseModel):
    source: str = Field(max_length=100_000)

class CompileRequest(SourceRequest):
    targets: list[str] = Field(max_length=16)

class CheckResponse(BaseModel):
    ok: bool
    diagnostics: list[DiagnosticModel]

class CompileResponse(CheckResponse):
    artifacts: list[ArtifactModel]
    targets: list[str]
```

`extra="forbid"` en todos los schemas evita que un cliente envíe campos que el
servidor ignore silenciosamente.

## Playground

`/playground` es HTML/CSS/JS sin dependencias externas. Llama a los mismos
endpoints y permite:

- editar el DSL con numeración de líneas;
- cargar un ejemplo seguro o uno inseguro;
- validar y compilar;
- seleccionar targets;
- ver diagnósticos y saltar a la línea;
- copiar o descargar cada artefacto.

## Docker

```bash
docker build -t dscops-api .
docker run --rm -p 8000:8000 dscops-api
```

El contenedor corre como UID 10001 y expone `/health` para el `HEALTHCHECK`.

## Integración

No hay estado en el servidor: cada petición es independiente. Para producción,
pon la API detrás de un proxy con TLS y limita el tamaño del cuerpo a nivel de
proxy además del límite de Pydantic.
