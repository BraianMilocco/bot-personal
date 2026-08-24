# Substep 2.1 — Factory LLM + transcripción
**Fecha:** 2026-08-24  |  **Commit:** step 2.1: cliente llm + transcripción

## Qué se hizo
- `app/agent/llm.py`: `get_client()` (AsyncOpenAI lazy, api_key/base_url por env),
  `transcribir(audio_bytes) -> str` con AUDIO_MODEL, y `extraer(schema, messages)`:
  structured output vía response_format json_schema + validación Pydantic + 1 retry
  reinyectando el error al modelo.
- 4 tests con cliente mockeado: extracción válida, retry ante JSON inválido, falla
  tras segundo intento, transcripción (verifica modelo y file tuple).
- README inicial con setup y smoke script manual del LLM (documentado, no automatizado).

## Archivos tocados
- app/agent/llm.py, tests/test_llm.py, README.md

## Decisiones tomadas
- SDK openai 3.3.1: se verificó por introspección que `chat.completions.create`,
  `parse` y `audio.transcriptions.create` existen; se usa `create` + json_schema
  (API estable y portable entre providers compatibles).
- Genérico PEP 695 (`extraer[T: BaseModel]`) para tipado del retorno.
- Cliente singleton module-level; los tests lo pisan con monkeypatch.

## DoD verificado
- `uv run pytest` → 20 passed (4 nuevos de llm, todos con mock, cero llamadas reales).
- Smoke script manual documentado en README.
- ruff check + format limpios.

## Pendientes/notas para el siguiente substep
- Ninguno.
