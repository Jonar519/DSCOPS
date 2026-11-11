# El lenguaje DSCOPS

## 1. Archivo

Un archivo `.dscops` es una secuencia de declaraciones. El orden no importa:
las referencias hacia adelante son válidas. Los comentarios empiezan con `#` y
llegan al final de la línea.

```text
start: statement*
?statement: service | database | link
service: "service" NAME "{" property* "}"
database: "database" NAME "{" property* "}"
link: NAME "->" NAME
property: NAME ":" value
?value: STRING | NUMBER | BOOL | call | object | NAME
call: NAME "(" [value ("," value)*] ")"
object: "{" [pair ("," pair)*] "}"
pair: NAME ":" value
```

## 2. Tipos

| Tipo | Ejemplos | Uso |
|---|---|---|
| `STRING` | `"python:3.12-slim"` | imagen, versión, tamaño, comando, secreto |
| `NUMBER` | `8000`, `3` | puerto, réplicas, tamaño numérico |
| `BOOL` | `true`, `false` | flags de entorno |
| `NAME` | `postgres`, `public` | engine, expose, valores de entorno |
| `call` | `secret("db_url")` | referencia a secreto |
| `object` | `{ cpu: "500m" }` | env y resources |

No hay arrays, condicionales, funciones definidas por el usuario ni expresiones
aritméticas. Esa restricción es intencional: el lenguaje describe, no programa.

## 3. `service`

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
```

| Propiedad | Obligatoria | Validación | Default |
|---|---|---|---|
| `image` | sí | string no vacío | — |
| `port` | no | entero 1–65535 | sin puerto |
| `replicas` | no | entero 1–1000 | `1` |
| `env` | no | objeto de escalares o `secret(...)` | `{}` |
| `expose` | no | `public`, `private`, `true`, `false` | `private` |
| `user` | no | string no vacío | sin definir |
| `resources` | no | objeto con `cpu` y/o `memory` | sin límites |
| `command` | no | string no vacío | comando de la imagen |

Propiedades desconocidas y duplicadas son errores (`SEM004`, `SEM003`).

### `env`

```text
env: {
  DB_URL: secret("db_url"),
  DEBUG: false,
  LOG_LEVEL: info,
  WORKERS: 4
}
```

Los escalares se convierten a texto (`false` → `"false"`). `secret("x")` es una
referencia; el compilador no conoce el valor.

### `resources`

```text
resources: { cpu: "500m", memory: "512Mi" }
```

- CPU se acepta en milicores (`500m`) o decimal (`0.5`). Compose convierte
  `500m` a `0.5`; Kubernetes conserva `500m`.
- Memoria se acepta con sufijo (`512Mi`, `1Gi`) o como número.
- Si falta CPU o memoria, SEC007 avisa.

### `command`

Se ejecuta con `sh -c` en Compose y Kubernetes. Es útil para imágenes base que
no traen una aplicación, por ejemplo el demo con `python -m http.server`.

## 4. `database`

```text
database main {
  engine: postgres
  version: "16"
  size: "20GB"
  expose: private
}
```

| Propiedad | Obligatoria | Validación | Default |
|---|---|---|---|
| `engine` | sí | identificador no vacío | — |
| `version` | no | escalar | versión estable del engine |
| `size` | no | string | `1Gi` |
| `expose` | no | public/private | `private` |
| `port` | no | entero 1–65535 | puerto del engine |

Engines con mapeo de imagen y puerto:

| Engine | Imagen base | Puerto | Volumen |
|---|---|---|---|
| `postgres` / `postgresql` | `postgres` | 5432 | `/var/lib/postgresql/data` |
| `mysql` | `mysql` | 3306 | `/var/lib/mysql` |
| `mariadb` | `mariadb` | 3306 | `/var/lib/mysql` |
| `mongodb` / `mongo` | `mongo` | 27017 | `/data/db` |
| `redis` | `redis` | 6379 | `/data` |

Un engine custom usa `engine:version` como imagen y `5432` como puerto por
defecto.

## 5. `link`

```text
api -> main
worker -> main
api -> cache
```

Una dependencia válida genera `depends_on` en Compose y `depends_on` en
Terraform. En Kubernetes no se traduce a un campo del manifiesto; la aplicación
debe reintentar la conexión. Una referencia inexistente produce `SEC008`.

## 6. Errores semánticos

| Código | Significado |
|---|---|
| `SEM001` | falta una propiedad obligatoria (`image` o `engine`) |
| `SEM002` | tipo o rango inválido |
| `SEM003` | propiedad, variable de entorno o límite duplicado |
| `SEM004` | propiedad o límite desconocido |
| `SEM005` | llamada inválida (solo `secret("nombre")` está permitido) |
| `SEC008` | link a recurso inexistente |
| `SEC009` | recurso duplicado |

## 7. Mapeo a artefactos

| DSL | Compose | Kubernetes |
|---|---|---|
| `service` | servicio + `deploy.replicas` | Deployment |
| `service` con `port` | `ports` o `expose` | Service + containerPort |
| `service` con `expose: public` | publica el puerto | Ingress |
| `database` | servicio + volumen + healthcheck | StatefulSet + PVC + Service |
| `link` | `depends_on` | no aplica |
| `replicas` | `deploy.replicas` | `spec.replicas` |
| `env` literal | variable | `value` |
| `secret("x")` | `${X}` | `secretKeyRef` |
| `resources` | `deploy.resources.limits` | `resources.limits` |
| `user` | `user` | `securityContext.runAsUser` |

## 8. Secretos

Compose:

```yaml
environment:
  DB_URL: ${DB_URL}
```

Kubernetes:

```yaml
env:
  - name: DB_URL
    valueFrom:
      secretKeyRef:
        name: api-secrets
        key: DB_URL
```

Antes de aplicar Kubernetes:

```bash
kubectl create secret generic api-secrets --from-literal=DB_URL='postgresql://...'
kubectl create secret generic main-secrets --from-literal=POSTGRES_PASSWORD='...'
```

## 9. Ejemplo mínimo

```text
service web {
  image: "nginx:1.27-alpine"
  port: 8080
  replicas: 2
  expose: public
  user: "101:101"
  resources: { cpu: "250m", memory: "128Mi" }
}

database db {
  engine: postgres
  version: "16"
  size: "10GB"
}

web -> db
```

## 10. Ejemplo inválido

```text
service api {
  image: "python:latest"
  port: 22
  replicas: 1
  env: { DB_PASSWORD: "admin123", DEBUG: true }
  expose: public
}

database main {
  engine: postgres
  expose: public
}

api -> ghost
```

`dscops check` reporta imagen sin tag, puerto sensible, secreto hardcodeado,
DEBUG público, réplicas insuficientes, falta de usuario/límites, base pública y
link inexistente.

## 11. Límites del lenguaje

- Sin variables ni reutilización de bloques.
- Sin secretos resueltos ni cifrado.
- Sin configuración por entorno (staging/producción).
- Sin arrays; `env` y `resources` son objetos.
- La gramática es LALR(1); si se agrega sintaxis ambigua, hay que rediseñarla o
  cambiar de parser.
