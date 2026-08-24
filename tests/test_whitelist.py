from unittest.mock import AsyncMock, MagicMock

from app.bot import handlers


def _update(telegram_id: int) -> MagicMock:
    update = MagicMock()
    update.effective_user.id = telegram_id
    update.message.reply_text = AsyncMock()
    return update


async def test_start_autorizado():
    await handlers.seed_users()
    handlers._whitelist_ts = 0.0  # fuerza refresh del cache
    update = _update(111111111)
    await handlers.cmd_start(update, None)
    texto = update.message.reply_text.call_args[0][0]
    assert "Braian" in texto
    assert "No autorizado" not in texto


async def test_start_id_ajeno_rechazado():
    handlers._whitelist_ts = 0.0
    update = _update(999999999)
    await handlers.cmd_start(update, None)
    assert update.message.reply_text.call_args[0][0] == "No autorizado."
