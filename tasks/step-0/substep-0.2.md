# Substep 0.2 — Estructura de app y configuración
**Fecha:** 2026-08-24  |  **Commit:** step 0.2: estructura de app y config

## Qué se hizo
- Árbol `app/` completo con módulos vacíos importables (bot/, agent/, db/, schemas, main).
- `config.py` con pydantic-settings: todas las env vars del plan, defaults donde el plan
  los define, `settings` singleton importable.
- Parser de `ALLOWED_USERS` (`usuarios_permitidos`) → lista de `UsuarioPermitido`.
- `.env.example` completo con comentarios y valores dummy; `.env` local copiado (gitignored).

## Archivos tocados
- app/ (todos los módulos), app/config.py, .env.example

## Decisiones tomadas
- `extra="ignore"` en Settings para tolerar env vars ajenas del entorno.
- Parser de whitelist en config (dataclass Pydantic) para reusar en seed de users (0.4).

## DoD verificado
- `uv run python -c "from app.config import settings"` con .env de ejemplo → imprime
  defaults y whitelist parseada OK.
- ruff check + format limpios.

## Pendientes/notas para el siguiente substep
- Ninguno.
