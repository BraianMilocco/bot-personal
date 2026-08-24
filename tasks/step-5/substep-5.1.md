# Substep 5.1 — Tools de consulta
**Fecha:** 2026-08-24  |  **Commit:** step 5.1: tools de consulta

## Qué se hizo
- `app/agent/tools.py`: DEFINICIONES (formato function-calling OpenAI) y
  `ejecutar_tool(nombre, argumentos, user_id)` para resumen_dia, resumen_semana,
  promedios_semana, comparar_semanas, tendencia_peso, historial_actividad — todas
  llaman al repository de consulta con sesión propia y `user_id` implícito (siempre
  el del mensaje; el LLM no puede consultar a otro usuario).
- Serializador `_json`: fechas → ISO, Decimal → string, filas ORM → dict por columnas.
- 4 tests: resumen_dia (800 kcal = 600+200, 45g prot, 7000 pasos), promedios/tendencia/
  historial con números exactos, tool desconocida → error JSON, definiciones completas.

## Archivos tocados
- app/agent/tools.py, tests/test_tools.py

## Decisiones tomadas
- Tools consultivas parametrizadas por fecha/días; nada de SQL generado por LLM
  (regla 7 del plan): solo nombres de tool fijos → repository.
- Decimal serializado como string para no perder precisión en el JSON.
- El seed de los tests commitea en sesión propia: las tools abren su propia sesión y
  no verían datos sin commitear de la fixture.

## DoD verificado
- `uv run pytest` → 56 passed; números exactos verificados a mano en asserts.
- ruff check + format limpios.

## Pendientes/notas para el siguiente substep
- 5.2 arma el loop de tool-calling usando DEFINICIONES + ejecutar_tool.
