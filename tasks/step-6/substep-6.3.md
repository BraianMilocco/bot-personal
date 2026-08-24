# Substep 6.3 — Resumen y históricos
**Fecha:** 2026-08-24  |  **Commit:** step 6.3: resumen de exámenes

## Qué se hizo
- `SYSTEM_RESUMEN_EXAMEN`: redacción usando SOLO valores y flags (en rango agrupados;
  fuera de rango destacados con "vale la pena consultarlo con tu médico"; comparación
  con estudio anterior del mismo tipo; tono de la regla 2 obligatorio).
- Nodo examen: tras persistir busca el estudio anterior del mismo tipo
  (`consultas.examen_anterior`) y se lo pasa al LLM de redacción; guarda el resumen en
  la fila del examen; el cierre (regla 4) se agrega SIEMPRE en código.
- Red de seguridad EN CÓDIGO: si el resumen del LLM contiene frases prohibidas
  ("tenés", "es grave", "diagnóstico", "padecés") o viene vacío → fallback
  `resumen_deterministico()` (agrupado en rango / fuera de rango / sin rango).
- `/examenes` (listado numerado, más reciente primero) y `/examen N` (resumen + valores
  con ⚠️ en los fuera de rango), sin LLM.
- `consultas.listar_examenes` y `consultas.examen_anterior`.

## Archivos tocados
- app/agent/prompts.py, app/agent/nodes.py, app/db/consultas.py, app/bot/handlers.py,
  tests/test_examen_resumen.py, tests/test_examen_ingesta.py (asserts al flujo nuevo),
  tests/test_examen_extraccion.py (ídem)

## Decisiones tomadas
- El recordatorio final NO depende del LLM: se concatena en código (regla 4 inviolable).
- El filtro de frases prohibidas actúa como red: LLM desobediente → resumen
  determinístico seguro (testeado con fixture "Tenés diabetes, es grave").

## DoD verificado
- `uv run pytest` → 76 passed: resumen cumple formato y tono; asserts de frases
  prohibidas en respuesta buena Y en fallback; comparación con estudio anterior viaja
  al LLM (verificado en messages); /examenes y /examen N correctos sin LLM.
- ruff check + format limpios.

## Pendientes/notas para el siguiente substep
- Ninguno.
