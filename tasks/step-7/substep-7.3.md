# Substep 7.3 — Resumen semanal proactivo
**Fecha:** 2026-08-24  |  **Commit:** step 7.3: resumen semanal

## Qué se hizo
- `app/bot/proactivo.py`: `armar_resumen_semanal` (encabezado determinístico con
  promedios de la semana + UNA sugerencia del LLM con system_sugerir),
  `enviar_resumen_semanal(bot)` (itera usuarios activos, envía por telegram_id,
  error de un usuario no frena a los demás) y `crear_scheduler` (AsyncIOScheduler,
  CronTrigger domingo 21:00 en la TZ configurada).
- `main.py`: el scheduler arranca junto al bot en el lifespan y se apaga al salir.
- 3 tests: job disparado manualmente envía mensaje correcto (chat_id + números del
  seed + sugerencia), LLM caído no explota el job, trigger programado dom 21:00.

## Archivos tocados
- app/bot/proactivo.py, app/main.py, tests/test_proactivo.py

## Decisiones tomadas
- Un solo job cron en la TZ global (settings.tz) que itera usuarios: con single-user
  alcanza; si hubiera usuarios en otras TZ reales, se programaría por-usuario (v2).
- Encabezado con números en código; el LLM solo aporta la sugerencia (números nunca
  redactados por el LLM).

## DoD verificado
- `uv run pytest` → 82 passed; job disparado manualmente en test envía el mensaje
  correcto al telegram_id correcto.
- ruff check + format limpios.

## Pendientes/notas para el siguiente substep
- Ninguno.
