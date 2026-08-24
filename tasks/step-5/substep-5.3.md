# Substep 5.3 — Comandos determinísticos
**Fecha:** 2026-08-24  |  **Commit:** step 5.3: comandos determinísticos

## Qué se hizo
- `/hoy`: resumen_dia con formato fijo (comidas con kcal, actividades, pasos, peso).
- `/semana`: promedios de la semana + línea por día (kcal, actividades, pasos).
- `/perfil`: campos del perfil o invitación a crearlo si no existe.
- Todos SIN LLM: repository directo con sesión propia; la fecha "hoy" sale de la TZ
  del usuario. /start actualizado con la lista de comandos.
- 4 tests: contenido exacto de cada comando con seed + assert de CERO llamadas al LLM;
  perfil vacío.

## Archivos tocados
- app/bot/handlers.py, tests/test_comandos.py

## Decisiones tomadas
- Formatos compactos de una línea por ítem (Telegram-friendly); sin Markdown para
  evitar problemas de escapado.

## DoD verificado
- `uv run pytest` → 62 passed; los 3 comandos responden correcto (números del seed
  verificados) y sin tocar el LLM (assert_not_called) — solo queries directas, <1s.
- ruff check + format limpios.

## Pendientes/notas para el siguiente substep
- Ninguno.
