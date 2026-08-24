# Substep 0.1 — Repo, uv y tooling
**Fecha:** 2026-08-24  |  **Commit:** step 0.1: repo, uv, ruff y tasks/

## Qué se hizo
- Repo git (ya existía con commit inicial del plan; se continuó sobre master).
- `uv init --python 3.12` (modo bare, sin main.py de ejemplo).
- Dependencias: fastapi, uvicorn, python-telegram-bot>=21,<22 (mayor pinneado), langgraph,
  langchain-openai, sqlalchemy[asyncio], asyncpg, alembic, pydantic-settings, openai,
  pymupdf, apscheduler. Dev: pytest, pytest-asyncio, httpx, ruff.
- Config ruff en pyproject: line-length 100, reglas E,F,I,UP,B,SIM, target py312.
- Config pytest: asyncio_mode auto.
- `.gitignore` (.env, .venv/, __pycache__, /data, caches).
- `tasks/` con PROGRESS.md (tabla índice) y `tasks/step-0/`.
- `uv.lock` commiteado.

## Archivos tocados
- pyproject.toml, uv.lock, .gitignore, tasks/PROGRESS.md, tasks/step-0/substep-0.1.md

## Decisiones tomadas
- Raíz del repo = `bot-asistente/` (directorio de trabajo del usuario); el nombre
  `asesor-personal/` del plan es ilustrativo de la raíz, no se creó subcarpeta.
- El repo ya tenía un commit ("primer commit" con el plan); no se reinicializó historia.

## DoD verificado
- `uv sync` limpio → "Resolved/Audited" sin errores.
- `uv run ruff check .` → "All checks passed!".
- `uv run ruff format --check .` → "2 files already formatted".

## Pendientes/notas para el siguiente substep
- Ninguno.
