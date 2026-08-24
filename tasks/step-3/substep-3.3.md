# Substep 3.3 — Registro por texto de los 4 tipos
**Fecha:** 2026-08-24  |  **Commit:** step 3.3: registro por texto completo

## Qué se hizo
- Nodo extraer generalizado con tabla `_EXTRACTORES` (intent → schema + prompt) para
  comida, actividad, peso y perfil.
- Nodo guardar: actividad tipo "pasos" → upsert en metricas_dia (no crea fila de
  actividad); sesiones → actividades; peso → pesos + actualiza perfil.peso_actual_kg;
  perfil → upsert solo de campos no nulos.
- Nodo responder con formato por tipo: "🍽/🏃/⚖️ Anotado, {nombre}: ... /deshacer si
  hubo error." + helper `_dia_legible` (hoy/ayer/dd-mm).
- Handlers: `mensaje_texto` (whitelist → estado → grafo → respuesta), `/deshacer`
  (borrar_ultimo_registro y dice qué borró), refactor `_autorizar`/`_log_mensaje`;
  cache de whitelist ahora guarda {user_id, nombre, tz} para armar el estado del grafo.
- 5 tests end-to-end (LLM mockeado): sesión de gym, pasos→metricas_dia (y NO
  actividades), peso (+perfil), perfil, /deshacer (borra y reporta; luego "no hay").

## Archivos tocados
- app/agent/nodes.py, app/bot/handlers.py, tests/test_registro_texto.py

## Decisiones tomadas
- "pasos" como tipo de actividad va SOLO a metricas_dia (upsert diario), según plan.
- Registrar peso también refresca perfil.peso_actual_kg (el perfil siempre al día
  para el bloque de contexto de 5.x).
- La identidad (user_id/nombre/tz) se resuelve en el handler vía whitelist; el grafo
  jamás la deriva del texto.

## DoD verificado
- `uv run pytest` → 42 passed; los 4 tipos por texto verificados contra db campo por
  campo; /deshacer borra el último y dice qué borró.
- ruff check + format limpios.

## Pendientes/notas para el siguiente substep
- Ninguno.
