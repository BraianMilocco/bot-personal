# Substep 0.3 — Docker
**Fecha:** 2026-08-24  |  **Commit:** step 0.3: docker compose + health

## Qué se hizo
- Dockerfile multi-stage: builder `ghcr.io/astral-sh/uv:python3.12-bookworm-slim` con
  `uv sync --frozen --no-dev`; runtime `python:3.12-slim-bookworm`, usuario non-root
  `appuser`, venv copiado, uvicorn en 8000.
- docker-compose: servicio `db` (postgres:16-alpine, healthcheck pg_isready, volumen
  nombrado `pgdata`, puerto 5432 expuesto para tests locales) y `app` (depends_on db
  healthy, restart unless-stopped, env_file .env, DATABASE_URL apunta a `db`).
- `main.py`: FastAPI con lifespan (engine async creado/dispuesto) y `GET /health` →
  `{"status":"ok","db":bool}` vía SELECT 1.

## Archivos tocados
- Dockerfile, docker-compose.yml, app/main.py

## Decisiones tomadas
- Engine async vive en `app.state` por ahora; en 1.1 se mueve a `db/session.py`.
- COPY de alembic quedó fuera del Dockerfile hasta que exista (1.1).
- Puerto 5432 publicado a host para correr tests contra el Postgres del compose (1.4/1.5).
- Volumen ./data montado en /app/data para PDFs de exámenes.

## DoD verificado
- `docker compose up -d --build` de cero → db Healthy, app Started.
- `curl localhost:8000/health` → `{"status":"ok","db":true}`.
- ruff check + format limpios.

## Pendientes/notas para el siguiente substep
- Dockerfile: agregar COPY de alembic/ y alembic.ini en 1.1.
