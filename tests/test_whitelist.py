from unittest.mock import AsyncMock, MagicMock

import pytest

from app.bot import handlers
from app.config import settings


def _update(telegram_id: int) -> MagicMock:
    update = MagicMock()
    update.effective_user.id = telegram_id
    update.message.reply_text = AsyncMock()
    return update


@pytest.fixture
def whitelist_seed(monkeypatch):
    """No depende del .env personal: fija la whitelist y limpia el cache."""
    monkeypatch.setattr(settings, "allowed_users", "111111111:Braian:+5493511111111")
    handlers._whitelist_ts = 0.0
    yield
    handlers._whitelist_ts = 0.0


async def test_start_autorizado(whitelist_seed):
    await handlers.seed_users()
    update = _update(111111111)
    await handlers.cmd_start(update, None)
    texto = update.message.reply_text.call_args[0][0]
    assert "Braian" in texto
    assert "No autorizado" not in texto


async def test_start_id_ajeno_rechazado(whitelist_seed):
    update = _update(999999999)
    await handlers.cmd_start(update, None)
    assert update.message.reply_text.call_args[0][0] == "No autorizado."
