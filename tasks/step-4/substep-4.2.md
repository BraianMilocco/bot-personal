# Substep 4.2 — Fotos de platos
**Fecha:** 2026-08-24  |  **Commit:** step 4.2: comidas por foto

## Qué se hizo
- `system_vision_plato(ahora)`: prompt de visión para platos (cocina argentina típica,
  caption del usuario MANDA sobre la imagen, reglas de tiempo diferido, estimaciones
  con confianza).
- Nodo `vision_plato`: foto clasificada "plato" → ComidaExtraida con VISION_MODEL;
  desde ahí el flujo es idéntico a texto (guardar/aclarar/responder por los mismos
  edges que extraer).
- Se quitó el placeholder de "plato" en vision_clasificar (quedan estudio/captura_app).
- Test DoD: foto → clasifica plato → extrae milanesa 600 kcal → fila en db con
  origen="imagen" y momento por hora local (calculado con momento_por_hora en el test).

## Archivos tocados
- app/agent/prompts.py, app/agent/nodes.py, app/agent/graph.py, tests/test_imagenes.py

## Decisiones tomadas
- vision_plato reusa `_despues_de_extraer` para el ruteo (mismo contrato que extraer):
  cero lógica nueva de guardado.

## DoD verificado
- `uv run pytest` → 51 passed; foto de plato registra comida con macros estimados,
  origen imagen y momento derivado de la hora local cuando la extracción no lo trae.
- ruff check + format limpios.

## Pendientes/notas para el siguiente substep
- Ninguno.
