"""Typer command-line interface.

This module only reads files, prints results and writes generated artifacts.
All compiler behavior lives in ``dscops.app``.
"""

from __future__ import annotations

from pathlib import Path

import typer
import uvicorn
from rich.console import Console
from rich.table import Table
from rich.text import Text

from dscops import __version__
from dscops.app import check_source, compile_source, target_infos
from dscops.domain.diagnostics import Diagnostic, Severity
from dscops.interfaces.formatting import print_diagnostics, print_summary

app = typer.Typer(
    name="dscops",
    help="DSCOPS: escribe tu infraestructura una vez, compílala segura.",
    no_args_is_help=False,
    invoke_without_command=True,
    rich_markup_mode="rich",
)
console = Console()


@app.callback()
def main(
    ctx: typer.Context,
    version: bool = typer.Option(
        False,
        "--version",
        help="Muestra la versión y sale.",
        is_eager=True,
    ),
) -> None:
    if version:
        console.print(f"dscops {__version__}")
        raise typer.Exit()
    if ctx.invoked_subcommand is None:
        console.print(ctx.get_help())
        raise typer.Exit()


@app.command()
def check(
    files: list[Path] = typer.Argument(..., help="Archivos .dscops a validar."),
    strict: bool = typer.Option(
        False,
        "--strict",
        help="Falla también cuando hay advertencias o avisos.",
    ),
) -> None:
    """Valida sintaxis, semántica y reglas de seguridad."""

    all_diagnostics: list[Diagnostic] = []
    failed = False
    for path in files:
        source = _read_source(path)
        if source is None:
            failed = True
            continue
        result = check_source(source)
        console.print(Text(str(path), style="bold"))
        print_diagnostics(console, str(path), source, result.diagnostics)
        print_summary(console, result.diagnostics)
        console.print()
        all_diagnostics.extend(result.diagnostics)
        if not result.ok or (
            strict
            and any(
                diagnostic.severity in {Severity.WARNING, Severity.INFO}
                for diagnostic in result.diagnostics
            )
        ):
            failed = True

    if len(files) > 1:
        print_summary(console, all_diagnostics)
    raise typer.Exit(code=1 if failed else 0)


@app.command()
def build(
    file: Path = typer.Argument(..., help="Archivo .dscops a compilar."),
    target: list[str] | None = typer.Option(
        None,
        "--target",
        "-t",
        help="Target a generar. Puede repetirse o separarse con comas.",
    ),
    out: Path = typer.Option(Path("out"), "--out", "-o", help="Directorio de salida."),
) -> None:
    """Compila un archivo y escribe los artefactos en disco."""

    source = _read_source(file)
    if source is None:
        raise typer.Exit(code=1)

    targets = _split_targets(target) if target else ["compose", "kubernetes"]
    result = compile_source(source, targets)
    print_diagnostics(console, str(file), source, result.diagnostics)
    print_summary(console, result.diagnostics)
    if not result.ok:
        raise typer.Exit(code=1)

    out_dir = out.resolve()
    written: list[Path] = []
    for artifact in result.artifacts:
        destination = (out_dir / artifact.path).resolve()
        if not destination.is_relative_to(out_dir):
            console.print(Text(f"ruta de artefacto insegura: {artifact.path}", style="red"))
            raise typer.Exit(code=1)
        destination.parent.mkdir(parents=True, exist_ok=True)
        destination.write_text(artifact.content, encoding="utf-8")
        written.append(destination)

    console.print()
    console.print(Text("Artefactos generados:", style="bold green"))
    for path in written:
        console.print(Text(f"  - {path}", style="green"))


@app.command()
def targets() -> None:
    """Lista los backends disponibles y sus alias."""

    table = Table(title="Targets de DSCOPS", show_lines=False)
    table.add_column("Nombre", style="bold")
    table.add_column("Alias", style="cyan")
    table.add_column("Descripción")
    for target in target_infos():
        table.add_row(target.name, ", ".join(target.aliases) or "-", target.description)
    console.print(table)


@app.command()
def serve(
    host: str = typer.Option("127.0.0.1", help="Interfaz de escucha."),
    port: int = typer.Option(8000, help="Puerto HTTP."),
    reload: bool = typer.Option(False, "--reload", help="Recarga en caliente para desarrollo."),
) -> None:
    """Levanta la API REST y el playground web."""

    console.print(Text(f"DSCOPS API en http://{host}:{port}  (docs: /docs)", style="bold green"))
    uvicorn.run(
        "dscops.interfaces.api.app:app",
        host=host,
        port=port,
        reload=reload,
    )


def _read_source(path: Path) -> str | None:
    try:
        return path.read_text(encoding="utf-8")
    except OSError as error:
        console.print(Text(f"no se pudo leer '{path}': {error}", style="bold red"))
        return None


def _split_targets(values: list[str]) -> list[str]:
    targets: list[str] = []
    for value in values:
        targets.extend(item.strip() for item in value.split(",") if item.strip())
    return targets


if __name__ == "__main__":  # pragma: no cover
    app()
