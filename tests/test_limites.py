"""DoD 8.1: exceso de mensajes recibe aviso amable; tokens visibles en logs."""

import logging
from unittest.mock import AsyncMock, MagicMock

from pydantic import BaseModel

from app.agent import llm
from app.bot import handlers
from tests.conftest import respuesta_llm


def _update() -> MagicMock:
    update = MagicMock()
    update.effective_user.id = 424242
    update.message.reply_text = AsyncMock()
    return update


async def test_exceso_de_mensajes_recibe_aviso(user_id, monkeypatch):
    monkeypatch.setattr(handlers, "RATE_LIMIT_MSGS", 3)
    monkeypatch.setattr(
        handlers,
        "usuario_autorizado",
        AsyncMock(return_value={"user_id": user_id, "nombre": "Test", "tz": "UTC"}),
    )
    update = _update()
    for _ in range(3):
        await handlers.cmd_start(update, None)
        assert "Pará un toque" not in update.message.reply_text.call_args[0][0]
    await handlers.cmd_start(update, None)  # 4to mensaje en el minuto
    assert "Pará un toque" in update.message.reply_text.call_args[0][0]


async def test_tokens_en_logs(cliente_mock, caplog):
    class Cosa(BaseModel):
        nombre: str

    respuesta = respuesta_llm('{"nombre": "x"}')
    respuesta.usage.prompt_tokens = 120
    respuesta.usage.completion_tokens = 15
    respuesta.usage.total_tokens = 135
    cliente_mock.chat.completions.create.return_value = respuesta

    with caplog.at_level(logging.INFO, logger="app.agent.llm"):
        await llm.extraer(Cosa, [{"role": "user", "content": "x"}])
        await llm.conversar([{"role": "user", "content": "x"}])

    registros = [r.message for r in caplog.records if "llm_tokens" in r.message]
    assert len(registros) == 2
    assert "prompt=120" in registros[0]
    assert "completion=15" in registros[0]
    assert "total=135" in registros[0]
