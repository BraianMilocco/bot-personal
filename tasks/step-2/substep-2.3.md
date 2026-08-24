# Substep 2.3 — Prompts base
**Fecha:** 2026-08-24  |  **Commit:** step 2.3: prompts base + tests

## Qué se hizo
- `app/agent/prompts.py`: `bloque_tiempo(ahora)` (fecha/hora/día actual inyectados +
  reglas de carga en diferido y coherencia horaria), `system_intent`,
  `system_extraccion_comida` (few-shots rioplatenses: "me morfé una milanga con papas
  anoche"), `system_extraccion_actividad` ("hice 9k pasos", "gym 45' fuerte"),
  `system_extraccion_peso`, `system_perfil`, y placeholders de visión/exámenes
  (steps 4 y 6).
- `tests/test_prompts.py`: extracción con respuestas fixture (LLM mockeado) para los
  4 casos del DoD; test de que el prompt inyecta fecha/hora/día y few-shots.
- Fixture `cliente_mock` y helper `respuesta_llm` movidos a conftest para reuso.

## Archivos tocados
- app/agent/prompts.py, tests/test_prompts.py, tests/conftest.py, tests/test_llm.py

## Decisiones tomadas
- Los prompts instruyen marcar `necesita_aclaracion` solo ante ambigüedad REAL y no
  preguntar en casos obvios (regla del plan: registrar sin fricción > precisión).
- Franjas horarias explícitas en el prompt (desayuno 07-10, almuerzo 12-15, merienda
  16-18, cena 20-23) para la coherencia horaria.

## DoD verificado
- `uv run pytest` → 33 passed. Fixtures cubren: comida simple (milanga → cena, 850 kcal),
  comida en diferido (cargada 23hs → desayuno de hoy), actividad con pasos (9k → 9000),
  caso ambiguo (sanguche 16hs → necesita_aclaracion="momento").
- ruff check + format limpios.

## Pendientes/notas para el siguiente substep
- Descubierto al correr la suite: el .env local ya tiene el telegram_id real del usuario
  (bot listo para probar en vivo cuando se cargue TELEGRAM_TOKEN real).
