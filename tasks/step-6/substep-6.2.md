# Substep 6.2 — Extracción y comparación
**Fecha:** 2026-08-24  |  **Commit:** step 6.2: extracción y comparación

## Qué se hizo
- `SYSTEM_EXAMEN` real: transcribir valores/rangos EXACTOS del estudio, jamás inventar
  rangos, sin interpretación.
- `parsear_numero()`: parseo defensivo ("95", "1,2", "<5", "38 mg/dl" → Decimal;
  "negativo"/vacío → None).
- `marcar_fuera_de_rango()`: comparación valor vs rango EN CÓDIGO; fuera_de_rango solo
  si el estudio trae rango Y el valor parsea; si no, NULL.
- Nodo `examen_extraer` real: PDF con texto → LLM de texto; escaneado/foto → visión;
  comparar en código; persistir examen + valores (guardar_examen); si la foto no tenía
  archivo, guarda el jpg hasheado en data/examenes/; respuesta con conteo y recordatorio
  de que la interpretación es del médico.
- Helper de archivos movido a `app/archivos.py` (compartido handler/nodo, sin ciclos).
- Tests: parseo defensivo (7 casos), marcado (dentro/fuera/"<5"/sin rango/no parseable),
  end-to-end con persistencia verificada campo por campo.

## Archivos tocados
- app/agent/prompts.py, app/agent/nodes.py, app/agent/graph.py, app/archivos.py,
  app/bot/handlers.py, tests/test_examen_extraccion.py, tests/test_examen_ingesta.py

## Decisiones tomadas
- "<5" se compara por su parte numérica (5): conservador y no rompe.
- fecha_estudio ausente → fecha de hoy (TZ usuario).
- Los tests de 6.1 que esperaban el placeholder se actualizaron al flujo real
  (siguen verificando que las 3 vías llegan al nodo).

## DoD verificado
- `uv run pytest` → 71 passed: estudio con rangos marca correctos (95 en 70-110 False,
  38 con min 40 True); estudio SIN rangos deja fuera_de_rango NULL; "<5" y "negativo"
  no rompen.
- ruff check + format limpios.

## Pendientes/notas para el siguiente substep
- 6.3: redacción del resumen con tono calibrado + /examenes.
