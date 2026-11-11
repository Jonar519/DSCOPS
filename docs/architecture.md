# Arquitectura de DSCOPS

## 1. Pipeline

```text
source .dscops
   │
   ▼
frontend (Lark LALR) ──> domain.ast.SourceFile
   │                         │
   │                         ▼
   │                  semantic.resolver ──> domain.model.InfraModel
   │                                              │
   │                         ┌────────────────────┴───────────────────┐
   │                         ▼                                        ▼
   │                  analysis.run_rules                     backends.registry
   │                         │                                        │
   │                         ▼                                        ▼
   │                  list[Diagnostic]                         list[Artifact]
   │                         └──────────────┬─────────────────────────┘
   │                                        ▼
   └──────────────────────────────> app.compile_source
                                            │
                              ┌─────────────┴─────────────┐
                              ▼                           ▼
                         CLI (Typer)                 API (FastAPI)
```

`app.check_source` ejecuta frontend + semántica + reglas. `app.compile_source`
hace lo mismo y, solo si no hay errores, invoca los backends solicitados.

## 2. Capas y regla de dependencias

```text
interfaces ──> app ──> frontend
                  ├──> semantic
                  ├──> analysis ──> domain
                  ├──> backends ──> domain
                  └──> domain
```

| Módulo | Responsabilidad | Puede importar |
|---|---|---|
| `domain` | AST, IR, `Diagnostic`, `Severity` | stdlib |
| `shared` | helpers puros (imágenes, tamaños, texto de env) | stdlib |
| `frontend` | lexer, parser, AST | `domain` |
| `semantic` | validación y construcción del IR | `domain`, `shared` |
| `analysis` | motor y reglas | `domain`, `shared` |
| `backends` | generación de artefactos | `domain`, `shared` |
| `app` | casos de uso | todos los anteriores |
| `interfaces` | CLI y HTTP | `app`, `domain` (solo tipos) |

`frontend`, `semantic`, `analysis` y `backends` **no se importan entre sí**. Eso
permite reemplazar el parser o un backend sin tocar el resto.

`interfaces` no contiene reglas: lee archivos o cuerpos HTTP, llama a `app` y
presenta el resultado.

## 3. Contratos

### Diagnóstico

```python
@dataclass(frozen=True, slots=True)
class Diagnostic:
    code: str
    severity: Severity          # error | warning | info
    message: str
    line: int | None = None
    column: int | None = None
    hint: str | None = None
    length: int | None = None
```

`length` permite dibujar el `^^^^` del CLI sin volver a parsear el texto.

### AST

El AST es literal: conserva cada propiedad y cada valor con su posición. No
decide si `port` es válido ni si `image` es obligatoria. Eso es semántica.

### IR neutral

```python
InfraModel(services=..., databases=..., links=...)
```

`Service` contiene `image`, `port`, `replicas`, `env`, `public`, `user`,
`resources`, `command` y posición. `Database` contiene `engine`, `version`,
`size`, `public`, `port`. Nada de Docker ni Kubernetes.

### Backend

```python
class Backend(Protocol):
    name: str
    description: str
    def generate(self, model: InfraModel) -> list[Artifact]: ...
```

`Artifact` es una ruta relativa más el contenido UTF-8 completo. El CLI decide
dónde escribir; la API lo devuelve en JSON.

### Regla

```python
class Rule(Protocol):
    code: str
    def check(self, model: InfraModel) -> list[Diagnostic]: ...
```

## 4. Flujo de una compilación

1. **Tamaño**: se rechaza un fuente de más de 100 000 caracteres (`CFG003`).
2. **Parseo**: `UnexpectedToken`, `UnexpectedCharacters` y `UnexpectedEOF` se
   convierten en `SYN001` con línea, columna y ayuda.
3. **Semántica**: tabla de símbolos, duplicados (`SEC009`), referencias
   (`SEC008`), propiedades obligatorias, tipos y valores por defecto.
4. **Seguridad**: se ejecutan las 8 reglas de `analysis` sobre el IR. Se
   ejecutan incluso si la semántica falló para mostrar más contexto.
5. **Corte**: si hay cualquier `ERROR`, no se genera nada (`ok: false`).
6. **Backends**: se resuelven todos los targets antes de generar. Un target
   desconocido produce `CFG002` y tampoco se escribe nada.
7. **Salida**: artefactos deterministas; el mismo modelo produce el mismo texto.

## 5. Registro simple

`backends/registry.py` es un diccionario con nombre canónico y alias. No hay
entry points, plugins dinámicos ni factories. Es suficiente para cuatro
backends y evita sobreingeniería.

`analysis/engine.py` mantiene una tupla `RULES`. Agregar una regla es agregar un
módulo y una entrada.

## 6. Generación de formatos

- **Compose / Kubernetes / GitHub Actions**: `dict` + `yaml.safe_dump`. No se
  concatenan strings YAML.
- **Terraform**: Jinja2 porque HCL no es un formato estructurado. Aun así, los
  datos se preparan en Python y se escapan comillas e interpolaciones.
- **Nombres de secretos**: sufijo `-secrets` en Kubernetes y variables `${...}`
  en Compose. Nunca se escribe el valor del secreto.

## 7. Seguridad por diseño

- El parser no ejecuta nada.
- El compilador no accede a red, base de datos ni secretos.
- La API no guarda estado ni escribe archivos.
- El CLI valida que la ruta del artefacto quede dentro de `--out`.
- La imagen Docker corre como UID 10001.
- Los ejemplos inseguros están separados y el CI no los trata como válidos.

## 8. Extensión

- **Nueva regla**: `analysis/rules/secXXX.py`, registrarla, dos tests.
- **Nuevo backend**: `backends/foo.py`, registrarlo, test de snapshot.
- **Nuevo target de lenguaje**: gramática + AST + semántica + IR + backends; por
  eso el MVP mantiene la gramática pequeña.

## 9. Decisiones

| Decisión | Motivo |
|---|---|
| Lark LALR | gramática declarativa, errores con posición, sin escribir un lexer a mano |
| IR separado | backends independientes y testeables |
| `dataclasses` en dominio | stdlib, sin Pydantic en el núcleo |
| Pydantic solo en API | validación en el borde |
| PyYAML para YAML | estructura verificable; sin bugs de indentación |
| Jinja2 solo para HCL | el texto no estructurado sí se beneficia de plantilla |
| Typer + Rich | CLI pequeña y salida legible |
| Sin plugins | KISS; un registro es suficiente |

## 10. Riesgos conocidos

- Los tags de imagen de las bases de datos se fijan por defecto, pero un engine
  custom puede terminar en `:latest`.
- Kubernetes referencia secretos que deben existir; no se generan valores.
- Terraform usa el provider Docker, no un clúster real.
- Compose con réplicas > 1 publica un rango de puertos; requiere Compose v2.
