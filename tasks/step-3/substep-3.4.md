# Substep 3.4 — Audio
**Fecha:** 2026-08-24  |  **Commit:** step 3.4: registro por audio

## Qué se hizo
- Handler `mensaje_audio` (voice y audio): límite 2 min y 10MB con mensajes amables,
  descarga por file_id (`get_file` + `download_as_bytearray`), transcripción con
  AUDIO_MODEL y reuso del flujo de texto (`_procesar_texto`) con origen="audio".
- Handler `mensaje_no_soportado`: catch-all amable listando formatos aceptados
  (video/stickers/etc; fotos y PDFs se les suman handlers propios en steps 4 y 6).
- Refactor: `_procesar_texto(update, usuario, texto, origen)` compartido texto/audio.
- 3 tests: nota de voz "hoy hice gym una hora" → actividad gym 60' origen=audio en db;
  audio >2min rechazado sin descargar; audio >10MB rechazado.

## Archivos tocados
- app/bot/handlers.py, tests/test_audio.py

## Decisiones tomadas
- Límite de tamaño 10MB (el plan pide "límite de tamaño" sin número; 2 min de opus
  pesa <2MB, 10MB da margen para audios reenviados).

## DoD verificado
- `uv run pytest` → 45 passed; test con transcripción mockeada verifica fila de
  actividad correcta (tipo gym, 60 min, origen audio) y respuesta al usuario.
- ruff check + format limpios.

## Pendientes/notas para el siguiente substep
- El handler de fotos (4.1) debe registrarse ANTES del catch-all de no soportados.
