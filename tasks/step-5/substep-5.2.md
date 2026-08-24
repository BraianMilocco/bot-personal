# Substep 5.2 — Charla multi-turno
**Fecha:** 2026-08-24  |  **Commit:** step 5.2: charla multi-turno

## Qué se hizo
- Nodo `consultar`: loop de tool-calling (máx 3 iteraciones + call de cierre sin tools
  si se agotan) con historial corto (ultimos_mensajes: 10 mensajes / 24hs) + bloque de
  contexto del usuario; guarda cada turno (user y assistant) en conversacion_mensajes.
- `bloque_contexto()`: perfil (objetivo, restricciones, peso) + tendencia de peso 30
  días + promedios de esta semana vs anterior, como texto compacto.
- `prompts.system_consultar`: personalidad + reglas duras (números EXACTOS de las
  tools, no recalcular, estimaciones con "~", nunca diagnóstico, derivar pedidos
  médicos) + contexto + bloque de tiempo.
- `llm.conversar(messages, tools)`: call de chat libre con tool-calling.
- `consultas.ultimos_mensajes` ahora acepta `horas` (ventana de 24hs).
- Ruteo: intent consultar → nodo consultar → END.
- conftest: helper `respuesta_tool_call` para mockear tool calls.
- Tests DoD: 3 turnos con repregunta — turno 1 usa tool y responde con números reales
  del seed (verifica que el JSON de la tool viajó al LLM), turno 2 lleva el historial
  del turno 1 en los messages, turno 3 responde directo; 6 filas en
  conversacion_mensajes; el bloque de contexto (peso 83.20) viaja en el system.

## Archivos tocados
- app/agent/nodes.py, app/agent/prompts.py, app/agent/llm.py, app/agent/graph.py,
  app/db/consultas.py, tests/conftest.py, tests/test_charla.py

## Decisiones tomadas
- Si el loop agota las 3 iteraciones pidiendo tools, se hace un call final SIN tools
  para forzar una respuesta en texto (nunca dejar al usuario sin respuesta).
- El historial guarda solo texto user/assistant (no los tool calls intermedios).

## DoD verificado
- `uv run pytest` → 58 passed; conversación de 3 turnos con repregunta coherente
  (historial verificado dentro de los messages del segundo turno).
- ruff check + format limpios.

## Pendientes/notas para el siguiente substep
- Ninguno.
