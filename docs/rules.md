# Reglas de seguridad

Cada regla vive en su propio archivo dentro de
`src/dscops/analysis/rules/`. El motor (`analysis/engine.py`) las ejecuta todas
y concatena los diagnósticos. Las reglas no generan artefactos: solo observan el
IR.

| Código | Severidad | Detecta | Archivo |
|---|---|---|---|
| `SEC001` | ERROR | secreto hardcodeado en env | `sec001_hardcoded_secret.py` |
| `SEC002` | WARNING | imagen `latest` o sin tag | `sec002_image_tag.py` |
| `SEC003` | ERROR | base de datos pública | `sec003_public_database.py` |
| `SEC004` | WARNING | servicio público sin puerto o con puerto sensible | `sec004_public_port.py` |
| `SEC005` | INFO | servicio público con una réplica | `sec005_single_replica.py` |
| `SEC006` | WARNING | contenedor root o sin `user` | `sec006_root_user.py` |
| `SEC007` | INFO | faltan límites de CPU/memoria | `sec007_resource_limits.py` |
| `SEC010` | WARNING | `DEBUG: true` en servicio público | `sec010_public_debug.py` |

`SEC008` (link inexistente) y `SEC009` (nombre duplicado) se detectan en
`semantic/resolver.py` porque requieren la tabla de símbolos.

## SEC001 — Secreto hardcodeado

**Detecta:** una variable cuyo nombre parece sensible (`PASSWORD`, `PASSWD`,
`SECRET`, `TOKEN`, `API_KEY`, `PRIVATE_KEY`, `ACCESS_KEY`, `AUTH`,
`DATABASE_URL`, `DB_URL`, `DSN`, `CONNECTION_STRING`) y cuyo valor es literal.

**No detecta:** `secret("db_url")`, que es una referencia.

```text
# mal
env: { DB_PASSWORD: "admin123" }

# bien
env: { DB_PASSWORD: secret("db_password") }
```

## SEC002 — Imagen sin versión

**Detecta:** imágenes sin tag (`python`) o con `:latest`. Un digest
(`@sha256:...`) cuenta como fijado.

```text
# mal
image: "python:latest"
image: "python"

# bien
image: "python:3.12-slim"
```

## SEC003 — Base de datos pública

**Detecta:** `database` con `expose: public`.

```text
# mal
database main { engine: postgres expose: public }

# bien
database main { engine: postgres expose: private }
```

**Por qué es error:** una base de datos accesible desde internet multiplica la
superficie de ataque. Debe vivir en la red privada del servicio.

## SEC004 — Puerto público

**Detecta:** un `service` con `expose: public` y:

- sin `port`, o
- con un puerto sensible: 22, 3306, 5432, 6379, 27017.

```text
# mal
service api { image: "x:1" expose: public }
service admin { image: "x:1" port: 22 expose: public }

# bien
service api { image: "x:1" port: 8000 expose: public }
```

## SEC005 — Una sola réplica pública

**Detecta:** `expose: public` con `replicas: 1` (o sin `replicas`, que vale 1).
Es un aviso de disponibilidad, no un error.

```text
# aviso
service api { image: "x:1" expose: public }

# mejor
service api { image: "x:1" replicas: 3 expose: public }
```

## SEC006 — Contenedor root

**Detecta:** falta `user` o el usuario es `root`, `0`, `0:0`, `root:root` o
empieza por `0:`/`root:`.

```text
# mal
service api { image: "x:1" }

# bien
service api { image: "x:1" user: "10001:10001" }
```

El backend Compose usa `10001:10001` por defecto y Kubernetes configura
`runAsNonRoot: true` salvo que el DSL pida explícitamente un usuario root. La
advertencia sirve para que la imagen tenga realmente ese usuario.

## SEC007 — Límites ausentes

**Detecta:** falta `resources`, `cpu` o `memory`.

```text
# mal
service api { image: "x:1" }

# bien
service api {
  image: "x:1"
  resources: { cpu: "500m", memory: "512Mi" }
}
```

Los límites se traducen a `deploy.resources.limits` (Compose) y
`resources.limits` (Kubernetes).

## SEC008 — Dependencia inexistente

**Detecta:** `origen -> destino` donde alguno no está declarado.

```text
service api { image: "x:1" }
api -> ghost       # SEC008
```

## SEC009 — Recurso duplicado

**Detecta:** dos `service`/`database` con el mismo nombre. El modelo conserva el
primero y el segundo se reporta.

```text
service api { image: "x:1" }
database api { engine: postgres }   # SEC009
```

## SEC010 — DEBUG público

**Detecta:** un servicio público con `DEBUG` en `true`, `1`, `yes` u `on` como
literal. Si `DEBUG` es un secreto, no se evalúa.

```text
# mal
service api { image: "x:1" expose: public env: { DEBUG: true } }

# bien
service api { image: "x:1" expose: public env: { DEBUG: false } }
```

## Cómo probar una regla

Cada regla tiene dos casos en `tests/unit/rules/test_rules.py`:

1. un modelo que la dispara;
2. un modelo que no la dispara (incluyendo el caso seguro).

Para una regla nueva:

```bash
pytest tests/unit/rules -q
ruff check src tests
mypy src
```

## Severidades

- `ERROR`: invalida la compilación; no se generan artefactos.
- `WARNING`: permite compilar, pero el CLI puede fallar con `--strict`.
- `INFO`: recomendación; no bloquea nada.
