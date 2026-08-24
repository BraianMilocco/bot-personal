# Substep 1.2 — Tablas de registro
**Fecha:** 2026-08-24  |  **Commit:** step 1.2: tablas de registro

## Qué se hizo
- Modelos `perfiles`, `pesos`, `comidas`, `actividades`, `metricas_dia` con todos los
  campos del modelo de datos del plan.
- Índices compuestos (user_id, fecha) en pesos, comidas, actividades; en metricas_dia
  lo cubre el UNIQUE(user_id, fecha).
- CheckConstraints en db para momento/origen/intensidad (enums del plan).
- NUMERIC(5,2) para pesos y NUMERIC(6,2) para distancia (Decimal, nunca float).
- `creado_en`/`actualizado_en` con server_default now() (timezone-aware).
- Migración autogenerada `b853fd98ebea_tablas_de_registro`.

## Archivos tocados
- app/db/models.py, alembic/versions/b853fd98ebea_tablas_de_registro.py

## Decisiones tomadas
- `perfiles.user_id` como PK+FK (el plan no le da id propio; 1:1 con users).
- Enums como CheckConstraint de strings, no tipo ENUM de Postgres: más simple de migrar.
- perfiles sin índice (user_id,fecha): no tiene fecha de negocio.

## DoD verificado
- `uv run alembic upgrade head` → aplica OK.
- `uv run alembic downgrade -1` → baja OK; re-upgrade OK (probado en secuencia).
- UNIQUE(user_id,fecha): `pg_constraint` muestra `uq_metricas_dia_user_fecha`.
- ruff check + format limpios.

## Pendientes/notas para el siguiente substep
- Ninguno.
