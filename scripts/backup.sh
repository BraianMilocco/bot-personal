#!/usr/bin/env bash
# Backup diario de Postgres (compose). Correr desde la raíz del repo.
# Cron sugerido (3:00 AM, conserva 14 días):
#   0 3 * * * cd /ruta/al/repo && ./scripts/backup.sh >> data/backups/backup.log 2>&1
set -euo pipefail

DESTINO="data/backups"
mkdir -p "$DESTINO"
ARCHIVO="$DESTINO/asesor_$(date +%Y%m%d_%H%M%S).sql.gz"

docker compose exec -T db pg_dump -U asesor -d asesor | gzip > "$ARCHIVO"
echo "backup ok: $ARCHIVO ($(du -h "$ARCHIVO" | cut -f1))"

# retención: borrar backups de más de 14 días
find "$DESTINO" -name "asesor_*.sql.gz" -mtime +14 -delete
