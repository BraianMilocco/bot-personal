# Substep 1.4 — Repository de escritura
**Fecha:** 2026-08-24  |  **Commit:** step 1.4: repository escritura + tests

## Qué se hizo
- `repository.py`: crear_comida, crear_actividad, crear_peso, upsert_metricas_dia
  (COALESCE: valores nuevos no-None pisan, None conserva), upsert_perfil (solo pisa
  campos recibidos), borrar_ultimo_registro (comida/actividad/peso por creado_en,
  devuelve tipo+descripción), guardar_examen(+valores), guardar_mensaje_conversacion,
  obtener_usuario(telegram_id).
- Funciones puras async que reciben session; sin lógica LLM.
- `tests/conftest.py`: fixtures `user_id` (db truncada + usuario de prueba) y `session`.
- 7 tests de escritura contra el Postgres del compose.

## Archivos tocados
- app/db/repository.py, app/db/models.py (pesos.creado_en), tests/conftest.py,
  tests/test_repository_escritura.py, alembic/versions/58c49362773b_pesos_creado_en.py

## Decisiones tomadas
- Se agregó `creado_en` a `pesos` (el plan no lo listaba): borrar_ultimo_registro
  compara por creado_en entre tipos y pesos no tenía timestamp comparable.
- borrar_ultimo_registro no toca metricas_dia: es un upsert diario, no un "registro".
- Test de borrar_ultimo usa transacciones separadas por registro (now() de Postgres es
  por transacción; en el uso real cada mensaje es una transacción).

## DoD verificado
- `uv run pytest` → 9 passed (7 de escritura + 2 de whitelist) contra Postgres del compose.
- ruff check + format limpios.

## Pendientes/notas para el siguiente substep
- Ninguno.
