# Substep 8.3 — Backup y cierre
**Fecha:** 2026-08-24  |  **Commit:** step 8.3: backup y cierre

## Qué se hizo
- `scripts/backup.sh`: pg_dump gzip del Postgres del compose a `data/backups/` con
  retención de 14 días; línea de cron sugerida documentada en el script y el README.
- README final: setup, tabla de formatos soportados, comandos, cambio de provider LLM
  por env, backup/restore, privacidad, smoke test manual.
- Fix operativo: `data/` la creaba docker como root (bind mount) → ni el backup ni el
  contenedor non-root podían escribir. Se corrigió el ownership (chown vía contenedor)
  y el README indica crear `data/` antes del primer `up`.
- Verificación final completa (abajo).

## Archivos tocados
- scripts/backup.sh, README.md, tasks/ (cierre)

## Decisiones tomadas
- Backup con retención simple de 14 días por `find -mtime`; sin herramientas extra.
- PDF del informe y features v2 quedan fuera, según el plan.

## DoD verificado
- Backup probado con restore REAL: `backup.sh` → dump 4K; restore a db `asesor_restore`
  → 11 tablas y filas de users intactas → drop. ✔
- Verificación final del proyecto:
  1. `docker compose down -v` + `up -d --build` de cero → migraciones solas, health
     `{"status":"ok","db":true}`. ✔
  2. Flujos end-to-end cubiertos por la suite (LLM mockeado): texto, audio, foto de
     plato, captura de Fit, PDF de examen, charla multi-turno, /informe. Prueba con
     Telegram real pendiente de que el usuario cargue su TELEGRAM_TOKEN. ✔
  3. `uv run pytest` → 90 passed; `ruff check` y `ruff format --check` limpios. ✔
  4. tasks/PROGRESS.md con TODOS los substeps en done. ✔

## Pendientes/notas para el siguiente substep
- Proyecto v1 completo. Para usar en producción: TELEGRAM_TOKEN y LLM_API_KEY reales
  en .env, y agregar el cron de backup del README en el server.
