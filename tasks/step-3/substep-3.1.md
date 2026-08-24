# Substep 3.1 — Grafo mínimo
**Fecha:** 2026-08-24  |  **Commit:** step 3.1: grafo mínimo registrar

## Qué se hizo
- `graph.py`: AgentState (telegram_id, user_id, nombre, tz, input_text, image_b64,
  pdf_text, origen, intent, extraccion, pendiente_aclaracion, respuesta); grafo
  clasificar → extraer → guardar → responder con edges condicionales;
  `procesar_mensaje()` como punto de entrada que NUNCA lanza (fallback amigable).
- `nodes.py`: decorador `_con_manejo` (log con nodo+telegram_id+intent, respuesta
  amigable ante excepción); nodo clasificar (IntentResult), extraer (ComidaExtraida
  para registrar_comida; otros intents → "todavía no sé"), guardar (crear_comida con
  session propia, resuelve fecha=hoy y momento por hora si faltan), responder
  (formato "🍽 Anotado, {nombre}: ... /deshacer si hubo error." o pregunta de aclaración).
- Helper `momento_por_hora` (franjas del día) y `ahora_usuario` (TZ del usuario).
- Tests de integración: texto → 2 calls LLM mockeados → fila en db verificada campo
  por campo → respuesta con datos; LLM caído → respuesta amigable, sin excepción.

## Archivos tocados
- app/agent/graph.py, app/agent/nodes.py, tests/test_graph.py

## Decisiones tomadas
- El handler resolverá user_id/nombre/tz ANTES del grafo (identidad nunca del LLM).
- `extraccion` guarda el objeto Pydantic directo en el estado (no dict).
- Errores: decorador por nodo + try/except en procesar_mensaje (doble red).
- En 3.1 solo registrar_comida guarda; el resto de intents se conecta en 3.3.

## DoD verificado
- `uv run pytest` → 35 passed; test end-to-end verifica descripcion, momento, kcal y
  raw_input en la fila de Postgres y los datos en la respuesta.
- ruff check + format limpios.

## Pendientes/notas para el siguiente substep
- Nodo aclarar con registro pendiente (3.2): hoy la aclaración solo pregunta, no retoma.
