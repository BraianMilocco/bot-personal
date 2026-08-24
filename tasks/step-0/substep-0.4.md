# Substep 0.4 — Bot mínimo con whitelist
**Fecha:** 2026-08-24  |  **Commit:** step 0.4: bot polling + whitelist db

## Qué se hizo
- Se ADELANTÓ 1.1 (permitido por el plan): `db/session.py` (engine async + session
  factory + context manager por mensaje), `db/models.py` con `users`, alembic async
  configurado (env.py lee settings + Base.metadata), migración inicial `users`.
- `bot/handlers.py`: `/start` con ayuda breve y saludo por nombre; whitelist contra db
  (`activo=true`) con cache en memoria TTL 60s; id ajeno → "No autorizado." + log warning;
  log estructurado por mensaje (telegram_id, tipo, latencia_ms — nunca token ni contenido).
- `seed_users()`: upsert de ALLOWED_USERS al arranque (on_conflict_do_update por telegram_id).
- `main.py`: lifespan arranca bot en polling; si el token es inválido loguea y la API
  sigue viva (evita crash-loop en dev con .env dummy).
- Dockerfile: COPY de alembic + `alembic upgrade head` antes de uvicorn.
- Tests: autorizado recibe ayuda con su nombre; id ajeno recibe "No autorizado.".

## Archivos tocados
- app/db/models.py, app/db/session.py, alembic/ (init + env.py + versions/03ebef908a79_users.py),
  alembic.ini, app/bot/handlers.py, app/main.py, Dockerfile, tests/test_whitelist.py,
  pyproject.toml (loop scope de pytest-asyncio)

## Decisiones tomadas
- 1.1 adelantado acá porque la whitelist necesita la tabla users (el plan lo prevé).
- Bot con token inválido no tumba la app: log de error y API viva — con token real arranca solo.
- Migraciones corren en el CMD del contenedor (`alembic upgrade head && uvicorn`).
- pytest-asyncio con loop de sesión: el pool de asyncpg no puede cruzar event loops.

## DoD verificado
- Tests: `uv run pytest` → 2 passed (autorizado responde, ajeno "No autorizado" y logueado).
- `docker compose up -d --build` → health `{"status":"ok","db":true}`; tabla users
  seedeada (`SELECT` muestra 111111111|Braian|t); bot loguea error claro con token dummy.
- ruff check + format limpios.

## Pendientes/notas para el siguiente substep
- 1.1 ya casi completo; en 1.1 solo verificar DoD formal (`alembic upgrade head` de cero
  en contenedor) y documentar.
- Usuario debe poner TELEGRAM_TOKEN real en .env para polling efectivo.
