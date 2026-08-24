# Asesor Personal

Bot de Telegram para registrar comidas, actividad, peso y exámenes médicos, con
análisis y sugerencias. Stack: Python 3.12, FastAPI, python-telegram-bot (polling),
LangGraph, SQLAlchemy async + Alembic, PostgreSQL 16, Docker Compose. Ver
`plan-asesor-personal.md` para el diseño completo.

## Setup rápido

```bash
cp .env.example .env   # completar TELEGRAM_TOKEN y LLM_API_KEY reales
docker compose up -d --build
curl localhost:8000/health   # → {"status":"ok","db":true}
```

Desarrollo local: `uv sync` y `uv run pytest` (necesita el Postgres del compose).

## Smoke test manual del cliente LLM

Con `LLM_API_KEY` real en `.env` (gasta tokens, correr a mano):

```bash
uv run python - <<'EOF'
import asyncio
from pydantic import BaseModel
from app.agent.llm import extraer

class Saludo(BaseModel):
    idioma: str
    texto: str

async def main():
    s = await extraer(Saludo, [{"role": "user", "content": "Saludame en español rioplatense"}])
    print(s)

asyncio.run(main())
EOF
```

Transcripción: mandar un `.ogg` corto por `transcribir(open("x.ogg","rb").read())`.
