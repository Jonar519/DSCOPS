"""Semantic analysis: AST -> neutral IR.

The resolver validates names, required properties, value types and links.
Security findings stay in ``dscops.analysis``; the only security-shaped checks
here are the two structural ones mandated by the language contract:
duplicate resources (SEC009) and dangling links (SEC008).
"""

from __future__ import annotations

from dataclasses import dataclass

from dscops.domain.ast import (
    BoolValue,
    CallValue,
    DatabaseDecl,
    LinkDecl,
    NameValue,
    NumberValue,
    ObjectValue,
    Property,
    ServiceDecl,
    SourceFile,
    StringValue,
    Value,
)
from dscops.domain.diagnostics import Diagnostic, Severity
from dscops.domain.model import Database, EnvValue, InfraModel, Link, Resources, Service
from dscops.shared.values import env_text

_SERVICE_PROPERTIES = {
    "image",
    "port",
    "replicas",
    "env",
    "expose",
    "user",
    "resources",
    "command",
}
_DATABASE_PROPERTIES = {"engine", "version", "size", "expose", "port"}
_RESOURCE_PROPERTIES = {"cpu", "memory"}
_SUPPORTED_CALLS = {"secret"}


@dataclass(frozen=True, slots=True)
class SemanticResult:
    model: InfraModel
    diagnostics: tuple[Diagnostic, ...]


def _error(
    code: str,
    message: str,
    *,
    line: int | None = None,
    column: int | None = None,
    hint: str | None = None,
    length: int | None = None,
) -> Diagnostic:
    return Diagnostic(
        code=code,
        severity=Severity.ERROR,
        message=message,
        line=line,
        column=column,
        hint=hint,
        length=length,
    )


def _property_map(
    name: str,
    properties: tuple[Property, ...],
    allowed: set[str],
    diagnostics: list[Diagnostic],
) -> dict[str, Property]:
    result: dict[str, Property] = {}
    for prop in properties:
        if prop.name in result:
            diagnostics.append(
                _error(
                    "SEM003",
                    f"propiedad duplicada '{prop.name}' en '{name}'",
                    line=prop.location.line,
                    column=prop.location.column,
                    hint="elimina una de las dos declaraciones",
                    length=len(prop.name),
                )
            )
            continue
        result[prop.name] = prop
        if prop.name not in allowed:
            diagnostics.append(
                _error(
                    "SEM004",
                    f"propiedad desconocida '{prop.name}' en '{name}'",
                    line=prop.location.line,
                    column=prop.location.column,
                    hint=f"propiedades válidas: {', '.join(sorted(allowed))}",
                    length=len(prop.name),
                )
            )
    return result


def _value_location(value: Value) -> tuple[int, int, int]:
    return value.location.line, value.location.column, value.location.length


def _decode_string(prop: Property, diagnostics: list[Diagnostic]) -> str | None:
    value = prop.value
    if isinstance(value, StringValue):
        return value.value
    line, column, length = _value_location(value)
    diagnostics.append(
        _error(
            "SEM002",
            f"'{prop.name}' espera una cadena entre comillas",
            line=line,
            column=column,
            hint=f'ejemplo: {prop.name}: "valor"',
            length=length,
        )
    )
    return None


def _decode_scalar(prop: Property, diagnostics: list[Diagnostic]) -> str | None:
    value = prop.value
    if isinstance(value, StringValue):
        return value.value
    if isinstance(value, NumberValue):
        return str(value.value)
    if isinstance(value, BoolValue):
        return env_text(value.value)
    if isinstance(value, NameValue):
        return value.value
    line, column, length = _value_location(value)
    diagnostics.append(
        _error(
            "SEM002",
            f"'{prop.name}' espera un valor escalar",
            line=line,
            column=column,
            hint="usa una cadena, un número, true/false o un identificador",
            length=length,
        )
    )
    return None


def _decode_identifier(prop: Property, diagnostics: list[Diagnostic]) -> str | None:
    value = prop.value
    if isinstance(value, (StringValue, NameValue)):
        return value.value
    line, column, length = _value_location(value)
    diagnostics.append(
        _error(
            "SEM002",
            f"'{prop.name}' espera un identificador (por ejemplo postgres)",
            line=line,
            column=column,
            hint=f"ejemplo: {prop.name}: postgres",
            length=length,
        )
    )
    return None


def _decode_positive_int(
    prop: Property,
    diagnostics: list[Diagnostic],
    *,
    maximum: int | None = None,
) -> int | None:
    value = prop.value
    if not isinstance(value, NumberValue):
        line, column, length = _value_location(value)
        diagnostics.append(
            _error(
                "SEM002",
                f"'{prop.name}' espera un número entero",
                line=line,
                column=column,
                hint=f"ejemplo: {prop.name}: 1",
                length=length,
            )
        )
        return None
    number = value.value
    if number <= 0 or (maximum is not None and number > maximum):
        suffix = f" entre 1 y {maximum}" if maximum is not None else " mayor que cero"
        line, column, length = _value_location(value)
        diagnostics.append(
            _error(
                "SEM002",
                f"'{prop.name}' debe ser un entero{suffix}",
                line=line,
                column=column,
                length=length,
            )
        )
        return None
    return number


def _decode_boolean_flag(
    prop: Property,
    diagnostics: list[Diagnostic],
    *,
    true_names: set[str],
) -> bool:
    value = prop.value
    if isinstance(value, BoolValue):
        return value.value
    if isinstance(value, NameValue) and value.value.lower() in true_names:
        return True
    if isinstance(value, NameValue) and value.value.lower() in {"private", "false", "no"}:
        return False
    if isinstance(value, StringValue) and value.value.lower() in true_names:
        return True
    if isinstance(value, StringValue) and value.value.lower() in {"private", "false", "no"}:
        return False
    line, column, length = _value_location(value)
    diagnostics.append(
        _error(
            "SEM002",
            f"'{prop.name}' espera 'public' o 'private'",
            line=line,
            column=column,
            hint="ejemplo: expose: public",
            length=length,
        )
    )
    return False


def _decode_env(prop: Property, diagnostics: list[Diagnostic]) -> dict[str, EnvValue]:
    value = prop.value
    if not isinstance(value, ObjectValue):
        line, column, length = _value_location(value)
        diagnostics.append(
            _error(
                "SEM002",
                "'env' espera un objeto { CLAVE: valor }",
                line=line,
                column=column,
                hint='ejemplo: env: { DB_URL: secret("db_url"), DEBUG: false }',
                length=length,
            )
        )
        return {}

    env: dict[str, EnvValue] = {}
    for pair in value.pairs:
        if pair.key in env:
            diagnostics.append(
                _error(
                    "SEM003",
                    f"variable de entorno duplicada '{pair.key}'",
                    line=pair.location.line,
                    column=pair.location.column,
                    length=len(pair.key),
                )
            )
            continue
        env_value = _decode_env_value(pair.key, pair.value, diagnostics)
        if env_value is not None:
            env[pair.key] = env_value
    return env


def _decode_env_value(key: str, value: Value, diagnostics: list[Diagnostic]) -> EnvValue | None:
    line = value.location.line
    column = value.location.column
    length = value.location.length
    if isinstance(value, CallValue):
        if value.name not in _SUPPORTED_CALLS:
            diagnostics.append(
                _error(
                    "SEM005",
                    f"función desconocida '{value.name}(...)' en la variable '{key}'",
                    line=line,
                    column=column,
                    hint='la única función disponible en env es secret("nombre")',
                    length=value.location.length,
                )
            )
            return None
        if len(value.arguments) != 1 or not isinstance(value.arguments[0], StringValue):
            diagnostics.append(
                _error(
                    "SEM005",
                    f"secret(...) en la variable '{key}' espera un único nombre entre comillas",
                    line=line,
                    column=column,
                    hint='ejemplo: DB_URL: secret("db_url")',
                    length=value.location.length,
                )
            )
            return None
        secret_name = value.arguments[0].value
        if not secret_name:
            diagnostics.append(
                _error(
                    "SEM005",
                    f"el nombre del secreto de '{key}' no puede estar vacío",
                    line=line,
                    column=column,
                    length=value.location.length,
                )
            )
            return None
        return EnvValue(
            value=secret_name,
            secret=True,
            line=line,
            column=column,
            length=length,
        )

    if isinstance(value, (StringValue, NumberValue, BoolValue, NameValue)):
        if isinstance(value, StringValue):
            text = value.value
        elif isinstance(value, NumberValue):
            text = str(value.value)
        elif isinstance(value, BoolValue):
            text = env_text(value.value)
        else:
            text = value.value
        return EnvValue(
            value=text,
            secret=False,
            line=line,
            column=column,
            length=length,
        )

    diagnostics.append(
        _error(
            "SEM002",
            f"el valor de '{key}' debe ser un escalar o secret(\"nombre\")",
            line=line,
            column=column,
            hint="no se permiten objetos anidados dentro de env",
            length=length,
        )
    )
    return None


def _decode_resources(prop: Property, diagnostics: list[Diagnostic]) -> Resources:
    value = prop.value
    if not isinstance(value, ObjectValue):
        line, column, length = _value_location(value)
        diagnostics.append(
            _error(
                "SEM002",
                "'resources' espera un objeto { cpu: ..., memory: ... }",
                line=line,
                column=column,
                hint='ejemplo: resources: { cpu: "500m", memory: "512Mi" }',
                length=length,
            )
        )
        return Resources()

    seen: dict[str, str] = {}
    for pair in value.pairs:
        if pair.key in seen:
            diagnostics.append(
                _error(
                    "SEM003",
                    f"límite duplicado '{pair.key}' en resources",
                    line=pair.location.line,
                    column=pair.location.column,
                    length=len(pair.key),
                )
            )
            continue
        if pair.key not in _RESOURCE_PROPERTIES:
            diagnostics.append(
                _error(
                    "SEM004",
                    f"límite desconocido '{pair.key}' en resources",
                    line=pair.location.line,
                    column=pair.location.column,
                    hint="límites válidos: cpu, memory",
                    length=len(pair.key),
                )
            )
            continue
        if isinstance(pair.value, StringValue):
            text = pair.value.value
        elif isinstance(pair.value, NumberValue):
            text = str(pair.value.value)
        else:
            line, column, length = _value_location(pair.value)
            diagnostics.append(
                _error(
                    "SEM002",
                    f'\'{pair.key}\' espera una cadena como "500m" o "512Mi"',
                    line=line,
                    column=column,
                    length=length,
                )
            )
            continue
        seen[pair.key] = text

    return Resources(cpu=seen.get("cpu"), memory=seen.get("memory"))


def _build_service(decl: ServiceDecl, diagnostics: list[Diagnostic]) -> Service:
    props = _property_map(decl.name, decl.properties, _SERVICE_PROPERTIES, diagnostics)

    image = ""
    image_prop = props.get("image")
    if image_prop is None:
        diagnostics.append(
            _error(
                "SEM001",
                f"el servicio '{decl.name}' no define 'image'",
                line=decl.location.line,
                column=decl.location.column,
                hint='agrega image: "python:3.12-slim"',
                length=len(decl.name),
            )
        )
    else:
        decoded = _decode_string(image_prop, diagnostics)
        if decoded is not None and not decoded.strip():
            diagnostics.append(
                _error(
                    "SEM002",
                    f"la imagen del servicio '{decl.name}' no puede estar vacía",
                    line=image_prop.location.line,
                    column=image_prop.location.column,
                    length=image_prop.location.length,
                )
            )
        else:
            image = decoded or ""

    port: int | None = None
    if (port_prop := props.get("port")) is not None:
        decoded_port = _decode_positive_int(port_prop, diagnostics, maximum=65535)
        port = decoded_port

    replicas = 1
    if (replicas_prop := props.get("replicas")) is not None:
        decoded_replicas = _decode_positive_int(replicas_prop, diagnostics, maximum=1000)
        if decoded_replicas is not None:
            replicas = decoded_replicas

    env: dict[str, EnvValue] = {}
    if (env_prop := props.get("env")) is not None:
        env = _decode_env(env_prop, diagnostics)

    public = False
    if (expose_prop := props.get("expose")) is not None:
        public = _decode_boolean_flag(expose_prop, diagnostics, true_names={"public"})

    user: str | None = None
    if (user_prop := props.get("user")) is not None:
        decoded_user = _decode_string(user_prop, diagnostics)
        if decoded_user is not None:
            if not decoded_user.strip():
                diagnostics.append(
                    _error(
                        "SEM002",
                        f"'user' del servicio '{decl.name}' no puede estar vacío",
                        line=user_prop.location.line,
                        column=user_prop.location.column,
                        length=user_prop.location.length,
                    )
                )
            else:
                user = decoded_user

    resources: Resources | None = None
    if (resources_prop := props.get("resources")) is not None:
        resources = _decode_resources(resources_prop, diagnostics)

    command: str | None = None
    if (command_prop := props.get("command")) is not None:
        command = _decode_string(command_prop, diagnostics)
        if command is not None and not command.strip():
            diagnostics.append(
                _error(
                    "SEM002",
                    f"'command' del servicio '{decl.name}' no puede estar vacío",
                    line=command_prop.location.line,
                    column=command_prop.location.column,
                    length=command_prop.location.length,
                )
            )
            command = None

    return Service(
        name=decl.name,
        image=image,
        port=port,
        replicas=replicas,
        env=env,
        public=public,
        user=user,
        resources=resources,
        command=command,
        line=decl.location.line,
        column=decl.location.column,
    )


def _build_database(decl: DatabaseDecl, diagnostics: list[Diagnostic]) -> Database:
    props = _property_map(decl.name, decl.properties, _DATABASE_PROPERTIES, diagnostics)

    engine = ""
    engine_prop = props.get("engine")
    if engine_prop is None:
        diagnostics.append(
            _error(
                "SEM001",
                f"la base de datos '{decl.name}' no define 'engine'",
                line=decl.location.line,
                column=decl.location.column,
                hint="agrega engine: postgres",
                length=len(decl.name),
            )
        )
    else:
        decoded_engine = _decode_identifier(engine_prop, diagnostics)
        if decoded_engine is not None:
            engine = decoded_engine.strip().lower()
            if not engine:
                diagnostics.append(
                    _error(
                        "SEM002",
                        f"el motor de '{decl.name}' no puede estar vacío",
                        line=engine_prop.location.line,
                        column=engine_prop.location.column,
                        length=engine_prop.location.length,
                    )
                )

    version: str | None = None
    if (version_prop := props.get("version")) is not None:
        version = _decode_scalar(version_prop, diagnostics)

    size: str | None = None
    if (size_prop := props.get("size")) is not None:
        size = _decode_string(size_prop, diagnostics)

    public = False
    if (expose_prop := props.get("expose")) is not None:
        public = _decode_boolean_flag(expose_prop, diagnostics, true_names={"public"})

    port: int | None = None
    if (port_prop := props.get("port")) is not None:
        port = _decode_positive_int(port_prop, diagnostics, maximum=65535)

    return Database(
        name=decl.name,
        engine=engine,
        version=version,
        size=size,
        public=public,
        port=port,
        line=decl.location.line,
        column=decl.location.column,
    )


def build_model(ast: SourceFile) -> SemanticResult:
    """Resolve ``ast`` into an ``InfraModel`` plus semantic diagnostics."""

    diagnostics: list[Diagnostic] = []
    seen: set[str] = set()
    declared: set[str] = set()

    for statement in ast.statements:
        if isinstance(statement, (ServiceDecl, DatabaseDecl)):
            declared.add(statement.name)
            if statement.name in seen:
                diagnostics.append(
                    _error(
                        "SEC009",
                        f"el recurso '{statement.name}' está declarado dos veces",
                        line=statement.location.line,
                        column=statement.location.column,
                        hint="usa un nombre único para cada service y database",
                        length=len(statement.name),
                    )
                )
            seen.add(statement.name)

    services: list[Service] = []
    databases: list[Database] = []
    built: set[str] = set()
    for statement in ast.statements:
        if isinstance(statement, ServiceDecl):
            if statement.name not in built:
                built.add(statement.name)
                services.append(_build_service(statement, diagnostics))
        elif isinstance(statement, DatabaseDecl) and statement.name not in built:
            built.add(statement.name)
            databases.append(_build_database(statement, diagnostics))

    links: list[Link] = []
    for statement in ast.statements:
        if not isinstance(statement, LinkDecl):
            continue
        if statement.source not in declared:
            diagnostics.append(
                _error(
                    "SEC008",
                    f"la dependencia apunta a un recurso inexistente: '{statement.source}'",
                    line=statement.location.line,
                    column=statement.location.column,
                    hint="declara el recurso o corrige el nombre",
                    length=len(statement.source),
                )
            )
        if statement.target not in declared:
            diagnostics.append(
                _error(
                    "SEC008",
                    f"la dependencia apunta a un recurso inexistente: '{statement.target}'",
                    line=statement.location.line,
                    column=statement.location.column + len(statement.source) + 4,
                    hint="declara el recurso o corrige el nombre",
                    length=len(statement.target),
                )
            )
        if statement.source in declared and statement.target in declared:
            links.append(
                Link(
                    source=statement.source,
                    target=statement.target,
                    line=statement.location.line,
                    column=statement.location.column,
                )
            )

    model = InfraModel(
        services=tuple(services),
        databases=tuple(databases),
        links=tuple(links),
    )
    return SemanticResult(model=model, diagnostics=tuple(diagnostics))
