"""HTTP routes for DSCOPS.

Routes are intentionally thin: parse the request with Pydantic, call one app
use case, serialize the result. No compiler logic lives here.
"""

from __future__ import annotations

from pathlib import Path

from fastapi import APIRouter, FastAPI
from fastapi.responses import FileResponse, RedirectResponse

from dscops import __version__
from dscops.app import check_source, compile_source, target_infos
from dscops.interfaces.api.schemas import (
    ArtifactModel,
    CheckResponse,
    CompileRequest,
    CompileResponse,
    DiagnosticModel,
    HealthResponse,
    SourceRequest,
    TargetModel,
)

_STATIC_DIR = Path(__file__).with_name("static")
_API_DESCRIPTION = """
Compilador declarativo de infraestructura con análisis de seguridad.

- `POST /v1/check`: valida sintaxis, semántica y reglas de seguridad.
- `POST /v1/compile`: valida y genera Docker Compose, Kubernetes, GitHub Actions o Terraform.
- `GET /v1/targets`: backends disponibles.
- `GET /docs`: documentación OpenAPI interactiva.
- `GET /playground`: editor web de prueba.

Los errores del usuario devuelven HTTP 200 con `ok: false` y diagnósticos.
Los errores de formato de la petición devuelven HTTP 422.
""".strip()

app = FastAPI(
    title="DSCOPS API",
    version=__version__,
    description=_API_DESCRIPTION,
    contact={"name": "DSCOPS Team", "url": "https://github.com/Jonar519/DSCOPS"},
    license_info={"name": "MIT"},
)
router = APIRouter(prefix="/v1")


@app.get("/", include_in_schema=False)
def root() -> RedirectResponse:
    return RedirectResponse(url="/playground", status_code=307)


@app.get("/health", response_model=HealthResponse, tags=["health"])
def health() -> HealthResponse:
    return HealthResponse(status="ok", version=__version__)


@app.get("/v1/health", response_model=HealthResponse, tags=["health"], include_in_schema=False)
def health_v1() -> HealthResponse:
    return health()


@app.get("/favicon.ico", include_in_schema=False)
def favicon() -> FileResponse:
    return FileResponse(_STATIC_DIR / "favicon.svg", media_type="image/svg+xml")


@app.get("/playground", include_in_schema=False)
def playground() -> FileResponse:
    return FileResponse(_STATIC_DIR / "playground.html", media_type="text/html")


@router.get("/targets", response_model=list[TargetModel], tags=["compiler"])
def targets() -> list[TargetModel]:
    """List every backend and its accepted aliases."""

    return [
        TargetModel(
            name=target.name,
            description=target.description,
            aliases=list(target.aliases),
        )
        for target in target_infos()
    ]


@router.post("/check", response_model=CheckResponse, tags=["compiler"])
def check(request: SourceRequest) -> CheckResponse:
    """Validate a source file without generating artifacts."""

    result = check_source(request.source)
    return CheckResponse(
        ok=result.ok,
        diagnostics=[DiagnosticModel.from_domain(item) for item in result.diagnostics],
    )


@router.post("/compile", response_model=CompileResponse, tags=["compiler"])
def compile_source_endpoint(request: CompileRequest) -> CompileResponse:
    """Validate and compile a source file into the requested targets."""

    result = compile_source(request.source, request.targets)
    return CompileResponse(
        ok=result.ok,
        diagnostics=[DiagnosticModel.from_domain(item) for item in result.diagnostics],
        artifacts=[
            ArtifactModel(path=artifact.path, content=artifact.content)
            for artifact in result.artifacts
        ],
        targets=list(result.targets),
    )


app.include_router(router)
