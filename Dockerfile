# syntax=docker/dockerfile:1
FROM python:3.12-slim

LABEL org.opencontainers.image.title="DSCOPS API" \
      org.opencontainers.image.description="Declarative Secure Compiler for Ops" \
      org.opencontainers.image.source="https://github.com/Jonar519/DSCOPS" \
      org.opencontainers.image.licenses="MIT"

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1

RUN groupadd --gid 10001 dscops \
    && useradd --uid 10001 --gid 10001 --create-home --shell /usr/sbin/nologin dscops

WORKDIR /app

COPY pyproject.toml README.md LICENSE ./
COPY src ./src

RUN python -m pip install . \
    && rm -rf /app/src /app/build /app/*.egg-info

USER 10001:10001

EXPOSE 8000

HEALTHCHECK --interval=30s --timeout=3s --start-period=10s --retries=3 \
    CMD ["python", "-c", "import urllib.request; urllib.request.urlopen('http://127.0.0.1:8000/health', timeout=2)"]

CMD ["uvicorn", "dscops.interfaces.api.app:app", "--host", "0.0.0.0", "--port", "8000"]
