# Substep 1.1 — Alembic async + users
**Fecha:** 2026-08-24  |  **Commit:** step 1.1: alembic + users

## Qué se hizo
- El grueso se implementó adelantado en 0.4 (session.py, models.py con users, alembic
  async, migración inicial). Acá se verificó el DoD formal de cero.
- Verificación: `docker compose down -v` (volúmenes borrados) + `up -d` → el contenedor
  corre `alembic upgrade head` de cero y la app levanta con db:true.

## Archivos tocados
- Solo tasks/ (código ya commiteado en 0.4).

## Decisiones tomadas
- Ninguna nueva; ver decisiones de 0.4 (sesión por mensaje con context manager, sin
  sesión global; NUMERIC/Decimal se aplica desde 1.2 donde hay medidas).

## DoD verificado
- `uv run alembic upgrade head` de cero en contenedor: log del contenedor muestra
  `Running upgrade  -> 03ebef908a79, users` tras `down -v`; health → `{"status":"ok","db":true}`.

## Pendientes/notas para el siguiente substep
- Ninguno.
