# Substep 6.1 — Ingesta de PDF y foto de estudio
**Fecha:** 2026-08-24  |  **Commit:** step 6.1: ingesta de estudios

## Qué se hizo
- Handler `mensaje_pdf` (filters.Document.PDF, máx 20MB): descarga, guarda el archivo
  con nombre hasheado (sha256[:16]) en `data/examenes/{user_id}/`, extrae texto con
  pymupdf; si el texto útil es <30 chars (escaneado) rasteriza la página 1 a PNG
  (200dpi) y la manda como imagen con `es_estudio=True`.
- Nodo `examen` (examen_extraer) en el grafo con placeholder honesto; llegan a él las
  3 vías: pdf_text (entrada→examen), PDF escaneado (es_estudio→examen) y foto
  clasificada "estudio" (vision→examen).
- Estado del grafo: `es_estudio` y `archivo_path` nuevos.
- Catch-all de no soportados excluye ahora Document.PDF.
- 6 tests: extracción de texto de PDF real (generado con pymupdf), rasterización de
  PDF sin texto, ruteo de las 3 vías, handler guarda archivo hasheado y arma el estado,
  PDF y foto de estudio llegan al placeholder end-to-end.

## Archivos tocados
- app/bot/handlers.py, app/agent/nodes.py, app/agent/graph.py, tests/test_examen_ingesta.py

## Decisiones tomadas
- La foto de estudio (por Telegram photo) no persiste archivo en 6.1: la clasificación
  ocurre dentro del grafo, después del handler. En 6.2 el nodo examen guardará la
  imagen si archivo_path viene vacío.
- PDF límite 20MB (los informes de laboratorio son chicos; margen para escaneos).

## DoD verificado
- `uv run pytest` → 68 passed; PDF con texto, PDF escaneado y foto de estudio llegan
  los tres al nodo de extracción (ruteo + end-to-end verificados).
- ruff check + format limpios.

## Pendientes/notas para el siguiente substep
- 6.2: reemplazar placeholder por extracción real + guardar imagen de foto de estudio.
