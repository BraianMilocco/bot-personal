# Substep 1.3 — Tablas de exámenes y conversación
**Fecha:** 2026-08-24  |  **Commit:** step 1.3: exámenes y conversación

## Qué se hizo
- Modelos `examenes` (fecha_estudio, tipo, archivo_path, resumen, creado_en),
  `examen_valores` (nombre, valor, unidad, ref_min/ref_max como TEXT del propio estudio,
  fuera_de_rango BOOL NULL) y `conversacion_mensajes` (rol con check, contenido, creado_en).
- Índices: (user_id, fecha_estudio) en examenes; examen_id en valores;
  (user_id, creado_en) en conversacion_mensajes para "últimos N".
- Migración `e9fc2f49adb3_examenes_y_conversacion`.

## Archivos tocados
- app/db/models.py, alembic/versions/e9fc2f49adb3_examenes_y_conversacion.py,
  alembic/script.py.mako (import moderno para futuras revisiones)

## Decisiones tomadas
- ref_min/ref_max y valor como TEXT: los estudios traen "<5", comas, etc.; el parseo
  numérico defensivo vive en 6.2, la db no fuerza número.
- archivo_path nullable: una foto de estudio puede procesarse sin persistir archivo aún.

## DoD verificado
- `alembic downgrade base` + `upgrade head`: las 3 migraciones aplican de cero en orden
  (users → registro → examenes/conversación).
- ruff check + format limpios.

## Pendientes/notas para el siguiente substep
- Ninguno.
