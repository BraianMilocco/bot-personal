# Substep 7.1 — Sugerencias con análisis cruzado
**Fecha:** 2026-08-24  |  **Commit:** step 7.1: sugerencias cruzadas

## Qué se hizo
- `system_sugerir(ahora, nombre, contexto)`: análisis cruzando comidas + actividad +
  pasos + tendencia de peso + objetivo; máx 3 sugerencias chicas; lenguaje de
  posibilidad obligatorio; prohibición explícita de suplementos con dosis, dietas
  médicas, medicación y síntomas → derivar al profesional.
- Nodo `sugerir`: bloque_contexto (reusa el de 5.2) + call sin tools; guarda ambos
  turnos en conversacion_mensajes (las repreguntas siguen por consultar con historial).
- Ruteo: intent sugerir → nodo sugerir → END.
- Tests DoD con seed diseñado (2600 kcal/día, 0 sesiones, peso +400g, objetivo bajar):
  la respuesta usa "puede deberse a"/"una opción es" y se verifica que el contexto REAL
  (kcal, sesiones, objetivo, delta) viajó en el system; pedido de dosis de creatina →
  deriva a médico/nutricionista sin dar la indicación.

## Archivos tocados
- app/agent/prompts.py, app/agent/nodes.py, app/agent/graph.py, tests/test_sugerencias.py

## Decisiones tomadas
- sugerir no usa tools: el bloque de contexto ya trae el cruce necesario (menos calls,
  menos latencia). Si el usuario repregunta con datos puntuales, cae en consultar.

## DoD verificado
- `uv run pytest` → 78 passed; ambos casos del DoD cubiertos (fixture + verificación
  del contexto y reglas en el prompt real).
- ruff check + format limpios.

## Pendientes/notas para el siguiente substep
- Ninguno.
