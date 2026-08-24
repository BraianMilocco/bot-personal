# Substep 4.1 — Clasificación de imagen
**Fecha:** 2026-08-24  |  **Commit:** step 4.1: clasificación de imagen

## Qué se hizo
- Handler `mensaje_foto`: toma la mejor resolución (photo[-1]), límite 10MB, descarga,
  base64 y entra al grafo con image_b64 + caption como input_text, origen="imagen".
  Registrado ANTES del catch-all de no soportados.
- Nodo `vision_clasificar`: primer call de visión (VISION_MODEL) con
  `SYSTEM_VISION_CLASIFICAR` real (ya no placeholder) → ClasificacionImagen y ruteo;
  "otro" → respuesta amable; plato/estudio/captura_app → placeholder temporal hasta
  4.2/4.3/6.x.
- Helper `_mensaje_con_imagen` (data URL base64 + caption como texto).
- Grafo: entrada → vision cuando hay image_b64.
- 5 tests: los 3 tipos clasifican bien (y el call usa vision_model + image_url),
  "otro" responde amable end-to-end, caption viaja junto a la imagen.

## Archivos tocados
- app/bot/handlers.py, app/agent/nodes.py, app/agent/graph.py, app/agent/prompts.py,
  tests/test_imagenes.py

## Decisiones tomadas
- El caption del usuario se agrega como parte de texto del mismo mensaje de visión
  (en 4.2 "el caption manda sobre la imagen").
- plato/estudio/captura_app responden placeholder honesto hasta sus substeps
  (comentado con `ponytail:`).

## DoD verificado
- `uv run pytest` → 50 passed; fixtures de plato/estudio/captura_app clasifican con
  visión mockeada; "otro" responde amable.
- ruff check + format limpios.

## Pendientes/notas para el siguiente substep
- 4.2 reemplaza el placeholder de "plato" por extracción real.
