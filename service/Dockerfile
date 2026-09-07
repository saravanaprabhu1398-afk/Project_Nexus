FROM python:3.12-slim AS base
ENV PYTHONUNBUFFERED=1 PYTHONDONTWRITEBYTECODE=1
WORKDIR /app

COPY --from=ghcr.io/astral-sh/uv:latest /uv /usr/local/bin/uv

COPY pyproject.toml ./
RUN uv pip install --system --no-cache .

COPY src/ ./src/
COPY alembic.ini ./
COPY migrations/ ./migrations/
ENV PYTHONPATH=/app/src

RUN useradd --create-home --uid 10001 nexus
USER nexus

EXPOSE 8000
HEALTHCHECK --interval=30s --timeout=3s CMD python -c "import urllib.request;urllib.request.urlopen('http://localhost:8000/healthz')"
CMD ["uvicorn", "nexus.main:app", "--host", "0.0.0.0", "--port", "8000"]
