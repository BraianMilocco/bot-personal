# Asesor Personal

Bot de Telegram personal para registrar **comidas, actividad física, peso y exámenes
médicos** en un solo lugar, con análisis cruzado, tendencias, sugerencias de hábitos e
informes para llevar al médico/nutricionista.

**Stack:** Python 3.12 · FastAPI · python-telegram-bot v21 (polling) · LangGraph ·
SQLAlchemy 2.0 async + Alembic · PostgreSQL 16 · Docker Compose · `uv` + `ruff`.
Diseño completo en `plan-asesor-personal.md`; bitácora de implementación en `tasks/`.

## Setup

```bash
cp .env.example .env      # completar TELEGRAM_TOKEN (BotFather) y LLM_API_KEY reales
mkdir -p data/examenes data/backups   # antes del primer up: si lo crea docker queda de root
docker compose up -d --build
curl localhost:8000/health   # → {"status":"ok","db":true}
```

Las migraciones corren solas al arrancar el contenedor. La whitelist sale de
`ALLOWED_USERS` (`telegram_id:nombre:telefono,...`) y se sincroniza a la db al arranque.

Desarrollo local: `uv sync`, luego `uv run pytest` (usa el Postgres del compose,
publicado en `localhost:5432`). Lint: `uv run ruff check .` y `uv run ruff format .`.

## Qué le podés mandar al bot

| Entrada | Qué hace |
|---|---|
| Texto | "me morfé una milanga anoche", "gym 45' fuerte", "pesé 82.5", "quiero bajar 5kg" |
| Nota de voz / audio (≤2 min) | se transcribe y sigue como texto |
| Foto de un plato | estima el plato y macros (~kcal) y lo registra |
| Captura de Google Fit / reloj | carga los pasos del día (la nueva pisa a la anterior) |
| PDF o foto de un examen | extrae valores y rangos DEL estudio, compara y resume |
| Preguntas | "¿qué días no entrené?", "¿cómo viene mi peso desde marzo?" (multi-turno) |

Carga en diferido soportada: "a la mañana comí tostadas" cargado a las 23hs va al
desayuno de hoy. Si algo es ambiguo, pregunta UNA vez y guarda.

## Comandos

- `/start` — ayuda
- `/hoy` `/semana` — resumen del día / la semana (sin LLM, instantáneo)
- `/perfil` — tu perfil (objetivo, restricciones, altura, peso)
- `/examenes` `/examen N` — exámenes cargados y detalle
- `/informe [medico|nutricionista]` — informe completo para llevar a la consulta
- `/deshacer` — borra el último registro

Todos los domingos 21:00 el bot manda un resumen de la semana + una sugerencia.

## Cambiar de provider LLM

Todo sale por env: `LLM_BASE_URL`, `LLM_MODEL`, `VISION_MODEL`, `AUDIO_MODEL`,
`LLM_API_KEY`. Cualquier provider con API compatible OpenAI (chat completions +
json_schema + tool calling) funciona sin tocar código.

## Backup

`scripts/backup.sh` hace `pg_dump` gzip a `data/backups/` con retención de 14 días.
Cron sugerido en el server:

```cron
0 3 * * * cd /ruta/al/repo && ./scripts/backup.sh >> data/backups/backup.log 2>&1
```

Restore:

```bash
gunzip -c data/backups/asesor_YYYYMMDD_HHMMSS.sql.gz | \
  docker compose exec -T db psql -U asesor -d asesor
```

## Privacidad

Datos de salud = datos sensibles: `.env` fuera de git, PDFs con nombre hasheado en
`data/` (fuera de git), logs sin contenido de mensajes (solo metadata: intent,
latencia, tokens). Uso personal; ver sección Privacidad del plan antes de abrirlo a
terceros.

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

Transcripción: `transcribir(open("x.ogg","rb").read())` con un `.ogg` corto.
