#!/usr/bin/env bash
# Deploy: pull + rebuild + up. Correr en el server, parado en la carpeta del proyecto.
set -euo pipefail
cd "$(dirname "$0")"

if git rev-parse --abbrev-ref '@{u}' >/dev/null 2>&1; then
    echo "==> git pull"
    git pull --ff-only
else
    echo "==> sin upstream configurado, salteo el pull" >&2
fi

echo "==> build"
docker compose build

echo "==> restart"
docker compose down
docker compose up -d

API_PORT=$(grep -E '^API_PORT=' .env 2>/dev/null | cut -d= -f2)
echo "==> esperando health..."
for i in $(seq 1 15); do
    sleep 2
    if curl -sf "localhost:${API_PORT:-18000}/health" | grep -q '"db":true'; then
        echo "==> OK"
        docker compose ps --format 'table {{.Service}}\t{{.State}}'
        exit 0
    fi
done

echo "==> FALLÓ el healthcheck, últimos logs:" >&2
docker compose logs --tail 30 api bot >&2
exit 1
