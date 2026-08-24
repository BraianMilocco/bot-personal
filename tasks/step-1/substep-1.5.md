# Substep 1.5 — Repository de consulta
**Fecha:** 2026-08-24  |  **Commit:** step 1.5: repository consulta + tests

## Qué se hizo
- `app/db/consultas.py`: resumen_dia, resumen_semana, promedios_semana (kcal/día,
  proteína/día, sesiones, pasos/día), comparar_semanas (actual vs anterior),
  tendencia_peso(dias) con delta, historial_actividad, ultimo_examen(tipo),
  valores_examen, ultimos_mensajes(user_id, n) y helper semana_de (lunes-domingo).
- 7 tests con seed diseñado y números calculados a mano.

## Archivos tocados
- app/db/consultas.py, tests/test_repository_consulta.py

## Decisiones tomadas
- Consultas en módulo propio `consultas.py` (el plan las llama "repository de consulta";
  separarlas de escritura deja archivos manejables y un import limpio para tools.py en 5.1).
- Semana = calendario (lunes a domingo), no ventana móvil: hace natural "¿y la semana
  pasada?" y comparar_semanas.
- kcal/proteína por día se dividen por días CON comidas registradas (no por 7): evita
  diluir promedios cuando el usuario no cargó todos los días.
- pasos_dia = promedio de metricas_dia con pasos no nulos.

## DoD verificado
- `uv run pytest` → 16 passed. Números exactos verificados a mano en asserts:
  kcal_dia 750 (1500/2 días), proteinas_dia 40, sesiones 2, pasos_dia 9000,
  semana anterior 2000/1/5000, delta_kg -0.50, últimos 10 mensajes en orden.
- ruff check + format limpios.

## Pendientes/notas para el siguiente substep
- Ninguno.
