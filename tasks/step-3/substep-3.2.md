# Substep 3.2 — Carga en diferido + nodo aclarar
**Fecha:** 2026-08-24  |  **Commit:** step 3.2: diferido + aclaración

## Qué se hizo
- Tabla `registros_pendientes` (user_id PK, tipo, payload JSON, campo, pregunta,
  creado_en) + migración. Repo: guardar_pendiente (upsert, uno por user),
  obtener_pendiente, borrar_pendiente.
- Nodos nuevos: `entrada` (carga pendiente al inicio de cada mensaje), `aclarar`
  (guarda el registro a medio completar y hace UNA pregunta corta), `completar`
  (fusiona payload pendiente + respuesta del usuario vía LLM, borra el pendiente y
  sigue a guardar).
- `pregunta_para()`: pregunta corta determinística por campo; caso 15-19hs sin momento
  → "¿Almuerzo o merienda?".
- Grafo: entry point ahora es `entrada` con edge condicional a completar/clasificar;
  extraer → aclarar cuando hay `necesita_aclaracion`.

## Archivos tocados
- app/db/models.py (RegistroPendiente), app/db/repository.py, app/agent/nodes.py,
  app/agent/graph.py, alembic/versions/e461a656d9be_registros_pendientes.py,
  tests/test_diferido_aclaracion.py

## Decisiones tomadas
- Pendiente en tabla propia (el plan ofrecía conversacion_mensajes o tabla de estado):
  tabla simple con PK user_id es más directa de consultar/borrar y sobrevive reinicios.
- `completar` fuerza `necesita_aclaracion=None` tras fusionar: evita loops de preguntas
  (regla del plan: ante duda real UNA pregunta; después registrar).
- Un solo pendiente por usuario: uno nuevo pisa al anterior.

## DoD verificado
- Test: "a la mañana comí tostadas con palta" (fixture con fecha hoy/desayuno) → fila
  con fecha=hoy, momento=desayuno. ✔
- Test: "comí un sanguche a las 16" sin momento → respuesta exacta "¿Almuerzo o
  merienda?", pendiente en db con campo=momento; "fue merienda" → fila guardada con
  momento=merienda y pendiente borrado. ✔
- `uv run pytest` → 37 passed; ruff limpio.

## Pendientes/notas para el siguiente substep
- Pendientes de actividad/peso: la tabla ya soporta `tipo`; completar hoy solo fusiona
  comida (los otros tipos se conectan en 3.3 si hace falta).
