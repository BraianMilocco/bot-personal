"""DoD 3.4: nota de voz → transcripción mockeada → flujo de texto → actividad en db."""

from datetime import date
from unittest.mock import AsyncMock, MagicMock

from sqlalchemy import select

from app.bot import handlers
from app.db.models import Actividad
from tests.conftest import respuesta_llm


def _update_voz(duracion: int = 30, file_size: int = 100_000) -> MagicMock:
    update = MagicMock()
    update.effective_user.id = 424242
    update.message.reply_text = AsyncMock()
    voz = MagicMock()
    voz.duration = duracion
    voz.file_size = file_size
    archivo = MagicMock()
    archivo.download_as_bytearray = AsyncMock(return_value=bytearray(b"ogg"))
    voz.get_file = AsyncMock(return_value=archivo)
    update.message.voice = voz
    update.message.audio = None
    return update


def _autorizado(monkeypatch, user_id):
    monkeypatch.setattr(
        handlers,
        "usuario_autorizado",
        AsyncMock(return_value={"user_id": user_id, "nombre": "Test", "tz": "UTC"}),
    )


async def test_nota_de_voz_registra_actividad(cliente_mock, user_id, session, monkeypatch):
    _autorizado(monkeypatch, user_id)
    hoy = date.today().isoformat()
    transcripcion = MagicMock()
    transcripcion.text = "hoy hice gym una hora"
    cliente_mock.audio.transcriptions.create.return_value = transcripcion
    cliente_mock.chat.completions.create.side_effect = [
        respuesta_llm('{"intent": "registrar_actividad"}'),
        respuesta_llm(f'{{"tipo": "gym", "duracion_min": 60, "fecha": "{hoy}"}}'),
    ]
    update = _update_voz()
    await handlers.mensaje_audio(update, None)

    fila = await session.scalar(select(Actividad).where(Actividad.user_id == user_id))
    assert fila.tipo == "gym"
    assert fila.duracion_min == 60
    assert fila.origen == "audio"
    assert "🏃 Anotado" in update.message.reply_text.call_args[0][0]


async def test_audio_muy_largo_rechazado(user_id, monkeypatch):
    _autorizado(monkeypatch, user_id)
    update = _update_voz(duracion=180)
    await handlers.mensaje_audio(update, None)
    assert "muy largo" in update.message.reply_text.call_args[0][0]
    update.message.voice.get_file.assert_not_called()


async def test_audio_muy_pesado_rechazado(user_id, monkeypatch):
    _autorizado(monkeypatch, user_id)
    update = _update_voz(file_size=50 * 1024 * 1024)
    await handlers.mensaje_audio(update, None)
    assert "pesado" in update.message.reply_text.call_args[0][0]
