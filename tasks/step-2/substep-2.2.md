# Substep 2.2 — Schemas de extracción
**Fecha:** 2026-08-24  |  **Commit:** step 2.2: schemas de extracción

## Qué se hizo
- `app/schemas.py`: IntentResult, ComidaExtraida (macros + confianza + fecha/momento/
  hora_aprox + necesita_aclaracion), ActividadExtraida (tipo/duración/intensidad/pasos/
  distancia + tiempos + necesita_aclaracion), PesoExtraido, PerfilUpdate,
  ExamenExtraido (lista de ValorExamen con ref_min/ref_max crudos), ClasificacionImagen.
- Validators: momento/intensidad/tipo/categoría como Literal (enum) con normalización
  a minúscula en mode="before"; Decimal para peso y distancia.
- 8 tests de validators con casos borde.

## Archivos tocados
- app/schemas.py, tests/test_schemas.py

## Decisiones tomadas
- `necesita_aclaracion` es el nombre del campo ambiguo (str | None), como pide 2.3.
- Intent incluye "otro" como fallback además de los 7 del grafo.
- ValorExamen.valor queda crudo (TEXT): el parseo numérico defensivo es de 6.2.
- confianza como Literal alta/media/baja (más robusto para el LLM que un float).

## DoD verificado
- `uv run pytest tests/test_schemas.py` → 8 passed; incluye momento inválido ("brunch")
  → ValidationError mencionando el campo, intensidad inválida, normalización a minúscula
  y Decimal verificado por tipo.
- ruff check + format limpios.

## Pendientes/notas para el siguiente substep
- Ninguno.
