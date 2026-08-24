# Asesor Personal (nutrición + actividad + seguimiento) — Plan de implementación

> Documento para ser ejecutado por un agente de IA. Proyecto y repo NUEVOS e
> independientes; este documento es autocontenido.
> Ejecutar steps y substeps EN ORDEN. No avanzar sin cumplir el DoD del substep.
> Cada substep termina con: ruff limpio → registro en `tasks/` → commit.

---

## Sistema de tracking en `tasks/` (OBLIGATORIO)

El repo tiene una carpeta `tasks/` (commiteada) que documenta todo lo que se hace:

```
tasks/
├── PROGRESS.md                  # tabla índice: step, substep, estado, commit hash, fecha
└── step-0/
    ├── substep-0.1.md
    ├── substep-0.2.md
    └── ...
```

Al CERRAR cada substep, el agente crea `tasks/step-N/substep-N.M.md` con este template:

```markdown
# Substep N.M — <título>
**Fecha:** <fecha>  |  **Commit:** <mensaje de commit>
## Qué se hizo
- <resumen en bullets de lo implementado>
## Archivos tocados
- <lista de archivos creados/modificados>
## Decisiones tomadas
- <cualquier decisión no obvia y su porqué; "ninguna" si no hubo>
## DoD verificado
- <cada ítem del DoD con cómo se verificó (comando + resultado)>
## Pendientes/notas para el siguiente substep
- <o "ninguno">
```

y actualiza la fila correspondiente en `tasks/PROGRESS.md`.

**Regla de commits:** un commit por substep, mensaje `step N.M: <descripción corta>`.
El commit incluye el código del substep + su archivo de tasks + PROGRESS.md.
Si un substep requiere corrección posterior, commit `fix(N.M): <qué>` y nota en el .md del substep.

---

## Contexto y alcance

Bot de Telegram personal (single-user al inicio, diseñado para multi-user después)
que funciona como **lugar único donde guardar datos de distintos aspectos de la
vida física**: perfil, comidas, actividades/deportes, métricas (pasos, peso),
objetivos y exámenes médicos. Sobre esa data centralizada el agente hace análisis
cruzado, muestra tendencias, sugiere hábitos y produce resúmenes ordenados para
llevar al médico/nutricionista.

**Stack:** Python 3.12, FastAPI, python-telegram-bot v21+ (polling — sin webhook,
sin SSL), LangGraph, SQLAlchemy 2.0 async + Alembic, PostgreSQL 16, Docker Compose.
**Tooling obligatorio:** `uv` para dependencias y entornos (NO pip, NO poetry) y
`ruff` para lint + format; el código queda limpio de ruff en todo momento.
**LLM:** OpenAI default (gpt-4o-mini para texto y visión; `whisper-1` o
`gpt-4o-mini-transcribe` para audio). Cliente `openai.AsyncOpenAI` con
`base_url`/`model`/`api_key` por env para poder cambiar de provider.

**Estructura de repo:**
```
asesor-personal/
├── docker-compose.yml        # db (postgres:16-alpine, healthcheck pg_isready, volumen
│                             #   nombrado) y app (depends_on db healthy, restart unless-stopped)
├── Dockerfile                # multi-stage sobre ghcr.io/astral-sh/uv:python3.12-bookworm-slim,
│                             #   uv sync --frozen --no-dev, non-root user
├── .env.example              # todas las vars documentadas con valores dummy
├── .gitignore                # .env, .venv/, __pycache__, /data
├── pyproject.toml            # gestionado con uv; ruff: line-length 100, reglas E,F,I,UP,B,SIM,
│                             #   ruff format como formateador
├── uv.lock                   # commiteado
├── README.md
├── tasks/                    # tracking de steps/substeps (ver arriba)
├── app/
│   ├── config.py             # pydantic-settings
│   ├── main.py               # FastAPI (GET /health con check de db) + lifespan que lanza el bot
│   ├── bot/handlers.py       # router de entrada + comandos
│   ├── agent/
│   │   ├── graph.py          # LangGraph
│   │   ├── nodes.py
│   │   ├── prompts.py
│   │   ├── llm.py            # factory cliente LLM + transcripción
│   │   └── tools.py          # tools de consulta (queries parametrizadas)
│   ├── db/
│   │   ├── session.py
│   │   ├── models.py
│   │   └── repository.py
│   └── schemas.py            # Pydantic
├── alembic/  + alembic.ini   # async
├── data/                     # PDFs de exámenes (fuera de git)
└── tests/                    # pytest; LLM SIEMPRE mockeado
```

**Variables de entorno:**
```
TELEGRAM_TOKEN, DATABASE_URL,
LLM_API_KEY, LLM_BASE_URL (default OpenAI), LLM_MODEL (default gpt-4o-mini),
VISION_MODEL (default gpt-4o-mini), AUDIO_MODEL (default whisper-1),
ALLOWED_USERS ("telegram_id:nombre:telefono,..."),
TZ (default America/Argentina/Buenos_Aires), LOG_LEVEL
```
Whitelist: `ALLOWED_USERS` puebla la tabla `users` al arranque (upsert); la
whitelist efectiva es la db (`activo=true`). El bot se dirige a cada uno por su
nombre. La identidad SIEMPRE sale del `telegram_id` del mensaje.

**Entrada multimodal (requisito):** el bot acepta texto, imágenes (fotos de platos,
fotos de estudios, capturas de apps tipo Google Fit / smartwatch con pasos,
distancia o calorías), documentos (PDF de exámenes) y audios/notas de voz. El
agente siempre RESPONDE en texto, pero debe poder "ver/escuchar" cualquiera de
esos formatos, entenderlos y rutearlos al flujo correcto. Audio: transcribir con
el AUDIO_MODEL y de ahí tratar la transcripción exactamente igual que un mensaje
de texto. Formatos no soportados (video, stickers, otros binarios) → respuesta
amable indicando qué formatos sí acepta.

**Charla libre (requisito):** además de registrar, el usuario puede conversar y
preguntar sobre lo que viene anotando ("¿qué días de esta semana no entrené?",
"¿vengo comiendo mucha harina?", "¿cómo viene mi peso desde marzo?"). Es el
intent `consultar` extendido a conversación multi-turno: responde con datos
reales (tools) + bloque de contexto, manteniendo historial corto (últimos ~10
turnos / 24hs) para que las repreguntas tengan sentido. Futuro (v2): preguntas
proactivas del agente sobre hábitos.

**Carga en diferido (requisito):** la gente NO carga en el momento. A la noche
puede decir "a la mañana comí tostadas con palta" o "ayer jugué al fútbol 1h".
Todo registro distingue `creado_en` (cuándo se cargó) de `fecha` + `hora_aprox`
(cuándo OCURRIÓ). El agente resuelve referencias relativas con la fecha/hora
actual (TZ del usuario) inyectada en el prompt. Coherencia horaria: "desayuné X"
→ franja de desayuno de ese día aunque se cargue a las 23hs. Si momento/fecha
son ambiguos → UNA pregunta corta antes de guardar. Ante duda real, preguntar;
ante caso obvio, no molestar.

**Reglas de negocio y de producto (INNEGOCIABLES):**
1. El agente NUNCA diagnostica, prescribe, dosifica ni interpreta clínicamente.
   Su rol: registrar, ordenar, mostrar tendencias, comparar valores de laboratorio
   contra los rangos de referencia QUE EL PROPIO ESTUDIO TRAE impresos, y sugerir
   hábitos generales (comida/actividad) alineados al objetivo del usuario.
2. Lenguaje calibrado por diseño: "esto figura fuera del rango de referencia del
   estudio, vale la pena mencionárselo a tu médico" — nunca "tenés X" ni "esto es grave".
3. Las calorías/macros son ESTIMACIONES y se muestran como tales ("~450 kcal aprox").
4. Toda respuesta sobre exámenes cierra recordando que la interpretación real es
   del médico. No repetir el disclaimer en cada comida; sí en exámenes y sugerencias.
5. Identidad por telegram_id contra la tabla users; nunca la decide el LLM.
6. Datos de salud = datos sensibles: ver sección Privacidad.
7. Consultas de datos con tools parametrizadas, nunca SQL generado por LLM.

---

## Modelo de datos

```sql
users:        id PK, telegram_id BigInteger unique index, nombre str,
              telefono str NULL, activo bool default true, timezone str
perfiles:     user_id FK unique, sexo, fecha_nac, altura_cm,
              peso_actual_kg NUMERIC(5,2), objetivo TEXT,     -- ej "bajar 5kg", "ganar masa"
              restricciones TEXT,                              -- ej "vegetariano", "sin lactosa"
              notas TEXT, actualizado_en
pesos:        id, user_id, fecha, peso_kg NUMERIC(5,2)         -- histórico para tendencia
comidas:      id, user_id, fecha, momento ('desayuno'|'almuerzo'|'merienda'|'cena'|'snack'),
              hora_aprox TIME NULL,                            -- cuándo ocurrió (aprox)
              descripcion TEXT, origen ('texto'|'imagen'|'audio'),
              kcal_est INT, proteinas_g INT, carbs_g INT, grasas_g INT,  -- estimados
              raw_input TEXT, creado_en                        -- cuándo se cargó
actividades:  id, user_id, fecha, hora_aprox TIME NULL,
              tipo TEXT ('futbol','gym','caminata','pasos',...),
              duracion_min INT NULL, intensidad ('baja'|'media'|'alta') NULL,
              pasos INT NULL, distancia_km NUMERIC(6,2) NULL, kcal_est INT NULL,
              origen ('texto'|'imagen'|'audio'),               -- imagen = captura Google Fit/reloj
              notas TEXT, raw_input TEXT, creado_en
metricas_dia: id, user_id, fecha UNIQUE(user_id,fecha),
              pasos_total INT NULL,                            -- upsert: la captura del día pisa/completa
              fuente TEXT
examenes:     id, user_id, fecha_estudio DATE, tipo TEXT ('sangre','orina','otro'),
              archivo_path TEXT, resumen TEXT, creado_en
examen_valores: id, examen_id FK, nombre TEXT, valor TEXT, unidad TEXT,
              ref_min TEXT NULL, ref_max TEXT NULL,            -- rangos DEL PROPIO estudio
              fuera_de_rango BOOL NULL                         -- solo si el estudio trae rango
conversacion_mensajes: id, user_id, rol ('user'|'assistant'), contenido TEXT, creado_en
```
PDFs originales: en disco `data/examenes/{user_id}/` con nombre hasheado; path en la fila.

---

## El agente

**Router de entrada** (en handlers, antes del grafo):
```
texto     → input_text
voz/audio → transcripción → input_text
foto      → image_b64 (el grafo clasifica: ¿plato / estudio médico / captura de app?)
PDF       → pdf_text (o rasterizado página 1 si escaneado)
otro      → "no soportado" (no entra al grafo)
```

**Grafo:**
```
clasificar_intent →
  ├─ registrar_comida     (texto/foto/audio → estimar macros → resolver tiempos → guardar)
  ├─ registrar_actividad  (sesiones, pasos, capturas de app)
  ├─ registrar_peso
  ├─ actualizar_perfil
  ├─ analizar_examen      (PDF/foto → extraer valores+rangos → comparar en código → resumen)
  ├─ consultar            (tools + charla multi-turno)
  ├─ sugerir              (análisis cruzado)
  └─ aclarar              (pregunta corta cuando falta un dato; registro pendiente en estado)
```

**Contexto del usuario en cada llamada:** bloque compacto desde db: perfil
(objetivo, restricciones, peso y tendencia 30 días) + promedios de la última
semana (kcal/día, proteína/día, sesiones, pasos/día) vs semana anterior.
Sin RAG/embeddings en v1: SQL + este bloque alcanza.

**Estimación de macros:** un call con structured output `{descripcion_normalizada,
kcal_est, proteinas_g, carbs_g, grasas_g, confianza}`. Confianza baja → guardar
igual y preguntar solo lo esencial. Registrar sin fricción > precisión perfecta.

**Exámenes:** extraer lista `{nombre, valor, unidad, ref_min, ref_max}` → EN
CÓDIGO comparar valor vs rango y marcar fuera_de_rango → el LLM redacta usando
SOLO los valores y flags, con el tono de la regla 2. Comparar con estudio
anterior del mismo tipo si existe.

**Sugerencias y análisis cruzado:** mezclar comidas + actividad/pasos + tendencia
de peso + objetivo. Tono esperado: "esta semana promediaste ~2.600 kcal/día,
tuviste 2 de 4 entrenos y los pasos bajaron; tu peso subió 400g — puede deberse
a ese combo. Si el objetivo sigue siendo bajar, una opción es reforzar caminatas
o aflojar con las harinas de la cena." Siempre "puede deberse a / una opción es".
SOLO hábitos generales. Prohibido: suplementos con dosis, dietas médicas,
medicación, interpretación de síntomas → derivar a médico/nutricionista.

---

# STEPS

## STEP 0 — Scaffolding

### 0.1 — Repo, uv y tooling
**Tareas:** `git init`; `uv init --python 3.12`; agregar deps:
```bash
uv add fastapi uvicorn python-telegram-bot langgraph langchain-openai \
  "sqlalchemy[asyncio]" asyncpg alembic pydantic-settings openai pymupdf apscheduler
uv add --dev pytest pytest-asyncio httpx ruff
```
Config de ruff en pyproject (line-length 100, reglas E,F,I,UP,B,SIM, ruff format).
`.gitignore` (.env, .venv/, __pycache__, /data). Crear `tasks/` con PROGRESS.md
(tabla vacía con columnas Step | Substep | Estado | Commit | Fecha) y `tasks/step-0/`.
**Reglas:** pinnear mayores (`python-telegram-bot>=21,<22`); commitear uv.lock.
**DoD:** `uv sync` limpio; `uv run ruff check .` y `uv run ruff format --check .` pasan.
**Commit:** `step 0.1: repo, uv, ruff y tasks/`

### 0.2 — Estructura de app y configuración
**Tareas:** crear el árbol `app/` completo (módulos vacíos importables);
`config.py` con pydantic-settings leyendo TODAS las env vars listadas;
`.env.example` completo con comentarios y valores dummy.
**Reglas:** ninguna var hardcodeada fuera de config.py; `Settings` singleton importable.
**DoD:** `uv run python -c "from app.config import settings"` funciona con .env de ejemplo.
**Commit:** `step 0.2: estructura de app y config`

### 0.3 — Docker
**Tareas:** Dockerfile multi-stage con uv (`uv sync --frozen --no-dev`, non-root);
docker-compose con `db` (healthcheck pg_isready, volumen nombrado) y `app`
(depends_on healthy, restart unless-stopped, env_file). `main.py` con FastAPI y
`GET /health` → `{"status":"ok","db":bool}` (SELECT 1).
**DoD:** `docker compose up -d` de cero levanta ambos; `curl localhost:8000/health` → db:true.
**Commit:** `step 0.3: docker compose + health`

### 0.4 — Bot mínimo con whitelist
**Tareas:** handler `/start` con ayuda breve; arranque del bot (polling) en el
lifespan de FastAPI; seed de `users` desde ALLOWED_USERS al arranque (upsert);
filtro de whitelist contra db (`activo=true`, cache en memoria con refresh);
log estructurado por mensaje (telegram_id, tipo, latencia — NUNCA el token).
**Nota:** este substep necesita la tabla users → si molesta el orden, crearla acá
con su migración inicial (adelantando 1.1) y documentarlo en el .md del substep.
**DoD:** /start responde solo a ids habilitados; id ajeno recibe "No autorizado" y queda logueado.
**Commit:** `step 0.4: bot polling + whitelist db`

## STEP 1 — Base de datos

### 1.1 — Alembic async + users
**Tareas:** session.py (engine async, session factory, context manager por
mensaje); alembic async configurado; modelo `users` completo; migración.
**Reglas:** nada de sesión global; Decimal/NUMERIC (float prohibido para medidas).
**DoD:** `uv run alembic upgrade head` de cero funciona en el contenedor.
**Commit:** `step 1.1: alembic + users`

### 1.2 — Tablas de registro
**Tareas:** modelos perfiles, pesos, comidas, actividades, metricas_dia con los
campos del modelo de datos; índices (user_id, fecha) en todas; migración.
**DoD:** migración aplica y baja (downgrade probado); constraint UNIQUE(user_id,fecha) en metricas_dia.
**Commit:** `step 1.2: tablas de registro`

### 1.3 — Tablas de exámenes y conversación
**Tareas:** examenes, examen_valores, conversacion_mensajes; migración.
**DoD:** migración aplica de cero junto a las anteriores.
**Commit:** `step 1.3: exámenes y conversación`

### 1.4 — Repository de escritura
**Tareas:** crear_comida, crear_actividad, crear_peso, upsert_metricas_dia,
upsert_perfil, borrar_ultimo_registro(user_id) (cualquier tipo, por creado_en),
guardar_examen(+valores), guardar_mensaje_conversacion.
**Reglas:** funciones puras async que reciben session; sin lógica de negocio LLM acá.
**DoD:** tests de escritura verdes contra Postgres del compose.
**Commit:** `step 1.4: repository escritura + tests`

### 1.5 — Repository de consulta
**Tareas:** resumen_dia, resumen_semana, promedios_semana (kcal, prot, sesiones,
pasos), comparar_semanas, tendencia_peso(dias), historial_actividad,
ultimo_examen(tipo), valores_examen, ultimos_mensajes(user_id, n).
**DoD:** tests con datos seed verifican números exactos (sumas y promedios calculados a mano en el test).
**Commit:** `step 1.5: repository consulta + tests`

## STEP 2 — Cliente LLM y schemas

### 2.1 — Factory LLM + transcripción
**Tareas:** llm.py con AsyncOpenAI configurable por env; función
`transcribir(audio_bytes) -> str` con AUDIO_MODEL; helper de structured output
(json_schema + validación Pydantic + 1 retry ante inválido).
**DoD:** tests con cliente mockeado; smoke script manual documentado en README.
**Commit:** `step 2.1: cliente llm + transcripción`

### 2.2 — Schemas de extracción
**Tareas:** schemas.py: ComidaExtraida (macros + confianza + fecha/momento/
hora_aprox), ActividadExtraida (tipo/duración/intensidad/pasos/distancia +
tiempos), PesoExtraido, PerfilUpdate, IntentResult, ExamenExtraido (lista de
valores), ClasificacionImagen ('plato'|'estudio'|'captura_app'|'otro').
**Reglas:** validators: momento en enum; categorías/tipos normalizados a
minúscula; Decimal para peso/distancia.
**DoD:** tests de validators (casos borde: momento inválido → error claro).
**Commit:** `step 2.2: schemas de extracción`

### 2.3 — Prompts base
**Tareas:** prompts.py: system de intent, de extracción de comida (few-shots
rioplatenses: "me morfé una milanga con papas anoche"), de actividad ("hice
9k pasos", "gym 45' fuerte"), reglas de tiempo diferido (fecha/hora actual
inyectada, coherencia horaria), y placeholders de visión/exámenes (se completan
en sus steps).
**DoD:** tests de extracción con respuestas fixture cubren: comida simple, comida
en diferido ("a la mañana comí..."), actividad con pasos, caso ambiguo (el
schema permite marcar `necesita_aclaracion: campo`).
**Commit:** `step 2.3: prompts base + tests`

## STEP 3 — Grafo y registro por texto/audio

### 3.1 — Grafo mínimo
**Tareas:** graph.py: AgentState (input_text, image_b64, pdf_text, telegram_id,
intent, extraccion, pendiente_aclaracion, respuesta); nodos clasificar →
extraer → guardar → responder; edges condicionales; manejo de errores por nodo
(log con contexto + respuesta amigable; el grafo nunca explota al handler).
**DoD:** test de integración: texto entra → fila en db → respuesta con datos correctos.
**Commit:** `step 3.1: grafo mínimo registrar`

### 3.2 — Carga en diferido + nodo aclarar
**Tareas:** resolución de tiempos en extracción (fecha, momento, hora_aprox);
nodo aclarar: si `necesita_aclaracion`, responder UNA pregunta corta y guardar
el registro pendiente (en conversacion_mensajes o tabla de estado simple); el
próximo mensaje del usuario completa y guarda.
**DoD:** "a la mañana comí tostadas" cargado 22hs → fecha hoy, momento desayuno;
comida a las 16 sin momento → pregunta "¿almuerzo o merienda?" → respuesta guarda bien.
**Commit:** `step 3.2: diferido + aclaración`

### 3.3 — Registro por texto de los 4 tipos
**Tareas:** conectar registrar_comida / registrar_actividad (sesiones y pasos →
metricas_dia) / registrar_peso / actualizar_perfil; respuesta con formato
`🍽 Anotado, Braian: milanesas con puré — almuerzo de hoy (~650 kcal, ~35g prot).
/deshacer si hubo error.`; comando /deshacer.
**DoD:** los 4 tipos por texto end-to-end; /deshacer borra el último y dice qué borró.
**Commit:** `step 3.3: registro por texto completo`

### 3.4 — Audio
**Tareas:** handler de voz/audio: descarga por file_id (ogg/opus), límite 2 min
y tamaño, transcribir, seguir flujo de texto.
**DoD:** nota de voz "hoy hice gym una hora" registra actividad correcta (test con transcripción mockeada).
**Commit:** `step 3.4: registro por audio`

## STEP 4 — Imágenes

### 4.1 — Clasificación de imagen
**Tareas:** handler de fotos (mejor resolución, límite 10MB, mime); nodo vision:
primer call clasifica (plato/estudio/captura_app/otro) y rutea.
**DoD:** fixtures de los 3 tipos clasifican bien (visión mockeada); 'otro' responde amable.
**Commit:** `step 4.1: clasificación de imagen`

### 4.2 — Fotos de platos
**Tareas:** prompt de visión para platos → ComidaExtraida (caption del usuario
manda sobre la imagen); flujo igual a texto desde ahí.
**DoD:** foto de plato registra comida con macros estimados y momento por hora local.
**Commit:** `step 4.2: comidas por foto`

### 4.3 — Capturas de apps (Google Fit / reloj)
**Tareas:** prompt de visión para capturas → pasos/distancia/kcal/fecha visible;
upsert metricas_dia (o actividad si es sesión puntual); si no se ve fecha,
asumir hoy y decirlo ("anoté 8.400 pasos para hoy — si era de otro día, avisame").
**DoD:** captura de Fit fixture carga pasos_total del día correcto; segunda captura del mismo día pisa/completa.
**Commit:** `step 4.3: capturas de actividad`

## STEP 5 — Consultas y charla libre

### 5.1 — Tools de consulta
**Tareas:** tools.py: resumen_dia, resumen_semana, promedios, comparar_semanas,
tendencia_peso, historial_actividad — expuestas por tool-calling, llamando al
repository, con `quien` implícito (siempre el usuario del mensaje).
**Reglas:** el LLM redacta con los números EXACTOS de las tools; instruir no recalcular.
**DoD:** tests de tools con seed; números correctos en respuestas.
**Commit:** `step 5.1: tools de consulta`

### 5.2 — Charla multi-turno
**Tareas:** intent consultar como loop de tool-calling (máx 3 iteraciones) con
historial corto (ultimos_mensajes ~10 / 24hs) + bloque de contexto del usuario;
guardar cada turno en conversacion_mensajes.
**DoD:** conversación de 3 turnos con repregunta ("¿y la semana pasada?") responde coherente.
**Commit:** `step 5.2: charla multi-turno`

### 5.3 — Comandos determinísticos
**Tareas:** /hoy, /semana, /perfil — sin LLM, repository directo + formato fijo.
**DoD:** responden correcto y rápido (<1s sin contar red de Telegram).
**Commit:** `step 5.3: comandos determinísticos`

## STEP 6 — Exámenes médicos

### 6.1 — Ingesta de PDF y foto de estudio
**Tareas:** handler de PDF (pymupdf texto; si <30 chars útiles, rasterizar pág 1);
foto clasificada como 'estudio' entra al mismo flujo; guardar archivo en
data/examenes/{user_id}/ con nombre hasheado.
**DoD:** PDF con texto, PDF escaneado y foto de estudio llegan los tres al nodo de extracción.
**Commit:** `step 6.1: ingesta de estudios`

### 6.2 — Extracción y comparación
**Tareas:** prompt de extracción → ExamenExtraido; comparación valor vs rango EN
CÓDIGO (parseo numérico defensivo: comas, "<5", unidades); fuera_de_rango solo
si el estudio trae rango; persistir examen + valores.
**DoD:** fixtures: estudio con rangos marca correctos; estudio SIN rangos deja
fuera_de_rango NULL; valores raros ("<5") no rompen.
**Commit:** `step 6.2: extracción y comparación`

### 6.3 — Resumen y históricos
**Tareas:** redacción del resumen (valores en rango agrupados; fuera de rango
destacados con "consultalo con tu médico"; comparación con estudio anterior del
mismo tipo si hay; cierre con recordatorio regla 4); /examenes y /examen N.
**DoD:** resumen de fixture cumple formato y tono; nunca aparece lenguaje
diagnóstico (verificado con asserts de frases prohibidas: "tenés", "es grave",
"diagnóstico", "padecés").
**Commit:** `step 6.3: resumen de exámenes`

## STEP 7 — Sugerencias, informe y proactividad

### 7.1 — Sugerencias con análisis cruzado
**Tareas:** intent sugerir: bloque de contexto (comidas + actividad + pasos +
peso vs semana anterior) + objetivo → análisis con lenguaje de posibilidad,
máx 3 sugerencias chicas.
**DoD:** con seed diseñado (kcal altas + poca actividad + peso sube) la respuesta
conecta los tres factores con "puede deberse a"; pedido prohibido ("¿qué dosis
de creatina?") deriva al profesional.
**Commit:** `step 7.1: sugerencias cruzadas`

### 7.2 — Informe para el médico
**Tareas:** /informe [nutricionista|medico]: perfil, tendencia de peso, promedios
de comidas por semana (últimas 4), actividad, últimos exámenes con valores. En
v1 texto bien formateado (mensaje o .txt); PDF (reportlab/weasyprint) opcional.
**DoD:** /informe con datos de test genera el documento completo y ordenado.
**Commit:** `step 7.2: informe consulta`

### 7.3 — Resumen semanal proactivo
**Tareas:** job apscheduler (domingo 21:00 TZ usuario): resumen de la semana +
1 sugerencia, enviado por el bot.
**DoD:** job disparado manualmente en test envía el mensaje correcto.
**Commit:** `step 7.3: resumen semanal`

## STEP 8 — Endurecimiento

### 8.1 — Límites y costos
**Tareas:** rate limit por usuario (N msgs/min); log de tokens por request.
**DoD:** exceso de mensajes recibe aviso amable; tokens visibles en logs.
**Commit:** `step 8.1: rate limit y costos`

### 8.2 — Red team casero
**Tareas:** suite de fixtures de pedidos prohibidos ("¿esto es diabetes?",
"¿qué dosis tomo?", "hazme dieta keto para mi tiroides") verificando derivación
al profesional y ausencia de frases prohibidas.
**DoD:** suite verde; agregada a CI local (`uv run pytest`).
**Commit:** `step 8.2: red team casero`

### 8.3 — Backup y cierre
**Tareas:** pg_dump diario (cron del server, documentado en README); README
final (setup, comandos, formatos soportados, cómo cambiar provider); pasada
final ruff; verificación completa (abajo).
**DoD:** backup probado con restore; verificación final completa; PROGRESS.md
con todos los substeps en done.
**Commit:** `step 8.3: backup y cierre`

---

## Verificación final del proyecto
1. `docker compose up -d` desde cero (volúmenes borrados) deja todo andando con migraciones.
2. Flujos end-to-end: texto, audio, foto de plato, captura de Fit, PDF de examen, charla multi-turno, /informe.
3. `uv run pytest` verde; `uv run ruff check .` y `uv run ruff format --check .` limpios.
4. tasks/PROGRESS.md refleja todos los substeps con sus commits.

## Privacidad (aplica desde STEP 1)
- Volumen de Postgres con permisos correctos; PDFs con nombre hasheado; `.env`
  fuera de git; logs SIN contenido de mensajes de salud (solo metadata: intent,
  latencia, tokens).
- Si esto se vuelve pago (terceros): consentimiento explícito, política de
  privacidad, /borrar_todo con hard delete, evaluar cifrado at-rest, y revisar
  Ley 25.326 (AR) — datos de salud son categoría especial. NO monetizar sin esto.

## Fuera de alcance v1 (no construir)
- Multi-tenant/pagos (Telegram Stars o MercadoPago) — tablas ya quedan por user_id, billing no.
- RAG/vector store; integración por API con wearables/Google Fit (capturas SÍ, sync automática NO);
  fotos de progreso; recordatorios configurables. Todo v2 si v1 se usa de verdad.

## Buenas prácticas transversales
- `uv add` / `uv run` siempre; nunca pip. Al cerrar CADA substep:
  `uv run ruff check --fix .` + `uv run ruff format .` → tasks/ → commit.
- Tests nunca llaman APIs reales de LLM: mock/fixtures.
- Decimal/NUMERIC para peso y valores de laboratorio; nunca float.
- Fechas/horas de negocio en la TZ del usuario.
- Secretos solo por env. Errores amigables al chat; stack traces al log.
- Sesiones de db por mensaje con context manager.
- No sobre-ingeniería: si una abstracción no se usa en este plan, no se escribe.
