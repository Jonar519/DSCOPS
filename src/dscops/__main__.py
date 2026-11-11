"""Allow ``python -m dscops`` as an alias for the console script."""

from __future__ import annotations

from dscops.interfaces.cli import app

if __name__ == "__main__":
    app()
