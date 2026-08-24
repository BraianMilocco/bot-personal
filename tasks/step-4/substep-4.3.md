# Substep 4.3 — Capturas de apps (Google Fit / reloj)
**Fecha:** 2026-08-24  |  **Commit:** step 4.3: capturas de actividad

## Qué se hizo
- `system_vision_captura(ahora)`: prompt de visión para capturas (pasos/distancia/kcal/
  fecha visible; conteo diario → tipo "pasos"; sesión puntual → actividad con duración;
  sin fecha visible → null; caption manda).
- Nodo `vision_captura`: ActividadExtraida con VISION_MODEL; marca `fecha_asumida`
  cuando la captura no trae fecha (guardar asume hoy).
- Responder: para actividad con `fecha_asumida` agrega "Si era de otro día, avisame."
- Ruteo: vision → vision_captura; comparte edges de guardado con vision_plato/extraer
  (pasos → upsert metricas_dia ya implementado en 3.3).
- Se quitó el placeholder de captura_app (queda solo "estudio" para 6.x).
- Test DoD: captura sin fecha → 5000 pasos hoy + aviso; segunda captura del día →
  8400 pisa a 5000, una sola fila en metricas_dia.

## Archivos tocados
- app/agent/prompts.py, app/agent/nodes.py, app/agent/graph.py, tests/test_imagenes.py

## Decisiones tomadas
- Sesión puntual detectada en captura (corrida con duración) va a actividades por el
  mismo guardar de 3.3; el prompt decide tipo "pasos" vs sesión.

## DoD verificado
- `uv run pytest` → 52 passed; captura carga pasos_total del día correcto y la segunda
  captura del mismo día pisa/completa (verificado: 1 fila, pasos 8400).
- ruff check + format limpios.

## Pendientes/notas para el siguiente substep
- Ninguno.
