# Substep 8.1 — Límites y costos
**Fecha:** 2026-08-24  |  **Commit:** step 8.1: rate limit y costos

## Qué se hizo
- Rate limit por usuario: ventana deslizante en memoria (deque de timestamps),
  máx 15 mensajes/minuto, chequeado en `_autorizar` (único choke point: aplica a
  comandos, texto, audio, fotos y PDF). Exceso → aviso amable + log warning.
- Log de tokens por request: `_log_tokens` en llm.py registra
  `llm_tokens modelo=... prompt=... completion=... total=...` en cada call de
  `extraer` y `conversar` (usage del SDK; tolerante a ausencia).
- Fixture autouse en conftest que limpia la ventana de rate limit entre tests.
- 2 tests: 4º mensaje con límite 3 recibe "Pará un toque..."; tokens visibles en
  caplog para extraer y conversar.

## Archivos tocados
- app/bot/handlers.py, app/agent/llm.py, tests/conftest.py, tests/test_limites.py

## Decisiones tomadas
- N=15 msgs/min (el plan no fija N; generoso para uso real, corta abuso).
- Ventana en memoria (single-process): suficiente para polling de un solo proceso.
- transcribir no loguea tokens (whisper no devuelve usage comparable).

## DoD verificado
- `uv run pytest` → 84 passed; exceso recibe aviso amable; tokens en logs verificados.
- ruff check + format limpios.

## Pendientes/notas para el siguiente substep
- Ninguno.
