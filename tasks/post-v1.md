# Post v1 — mejoras tras el cierre del plan

## 2026-08-24 — Menú de comandos + seed por migración
**Commit:** post: menú de comandos + migración seed ALLOWED_USERS

### Qué se hizo
- Menú de comandos publicado en Telegram (`setMyCommands` en el arranque, botón "/"
  del chat): start, hoy, semana, perfil, examenes, examen, informe, deshacer.
  Test verifica que el menú cubre exactamente los CommandHandler registrados.
- Migración `c1aaf360f1d2_seed_allowed_users`: inserta los usuarios de ALLOWED_USERS
  que no estén en la db (ON CONFLICT DO NOTHING; no pisa datos editados; downgrade
  no borra). Ahora los users existen apenas corren las migraciones, sin esperar al
  arranque de la app. El seed del startup sigue (actualiza nombre/teléfono).
- Fix de privacidad: httpx logueaba la URL de la API de Telegram CON el token en
  INFO; se silenció a WARNING (regla del plan: nunca el token en logs).

### Verificado
- `alembic downgrade base && upgrade head` → usuario real de ALLOWED_USERS insertado;
  downgrade -1 + upgrade → idempotente (count 1).
- Contenedor rebuildeado con token real: getMe y setMyCommands 200, polling activo,
  y el token ya no aparece en los logs (grep = 0).
- `uv run pytest` → 92 passed; ruff limpio.
