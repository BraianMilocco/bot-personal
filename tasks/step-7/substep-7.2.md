# Substep 7.2 — Informe para el médico
**Fecha:** 2026-08-24  |  **Commit:** step 7.2: informe consulta

## Qué se hizo
- `app/informe.py`: `generar_informe()` determinístico (sin LLM) con secciones: perfil,
  peso de los últimos 30 días con variación, promedios de alimentación por semana
  (últimas 4), actividad de los últimos 28 días (conteo por tipo + minutos totales) y
  últimos 3 exámenes con valores y marca [FUERA DE RANGO DEL ESTUDIO]. Encabezado
  aclara que son datos autorreportados y estimaciones (regla 3).
- `/informe [nutricionista|medico]`: mensaje de texto; si supera ~3500 chars se manda
  como `.txt` adjunto (límite de Telegram). PDF (opcional en el plan) no se hizo.
- /start actualizado con /examenes e /informe.
- Test DoD: seed de 2 semanas + examen → verifica cada sección y número exacto,
  encabezado por destinatario, y CERO llamadas al LLM.

## Archivos tocados
- app/informe.py, app/bot/handlers.py, tests/test_informe.py

## Decisiones tomadas
- Informe 100% determinístico: lo que va al médico no debe depender de la redacción
  del LLM (números exactos, cero alucinación).
- PDF (reportlab/weasyprint) omitido: el plan lo marca opcional y el .txt cubre v1.

## DoD verificado
- `uv run pytest` → 79 passed; /informe con datos de test genera el documento completo
  y ordenado (todas las secciones verificadas).
- ruff check + format limpios.

## Pendientes/notas para el siguiente substep
- Ninguno.
