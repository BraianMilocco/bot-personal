from unittest.mock import MagicMock

import pytest
from pydantic import BaseModel, ValidationError

from app.agent import llm
from tests.conftest import respuesta_llm as _respuesta


class Cosa(BaseModel):
    nombre: str
    cantidad: int


async def test_extraer_valido(cliente_mock):
    cliente_mock.chat.completions.create.return_value = _respuesta(
        '{"nombre": "milanesa", "cantidad": 2}'
    )
    cosa = await llm.extraer(Cosa, [{"role": "user", "content": "dos milanesas"}])
    assert cosa == Cosa(nombre="milanesa", cantidad=2)
    assert cliente_mock.chat.completions.create.call_count == 1


async def test_extraer_retry_ante_invalido(cliente_mock):
    cliente_mock.chat.completions.create.side_effect = [
        _respuesta('{"nombre": "milanesa"}'),  # falta cantidad → inválido
        _respuesta('{"nombre": "milanesa", "cantidad": 1}'),
    ]
    cosa = await llm.extraer(Cosa, [{"role": "user", "content": "milanesa"}])
    assert cosa.cantidad == 1
    assert cliente_mock.chat.completions.create.call_count == 2


async def test_extraer_falla_tras_retry(cliente_mock):
    cliente_mock.chat.completions.create.side_effect = [
        _respuesta("no soy json"),
        _respuesta("sigo sin ser json"),
    ]
    with pytest.raises(ValidationError):
        await llm.extraer(Cosa, [{"role": "user", "content": "x"}])
    assert cliente_mock.chat.completions.create.call_count == 2


async def test_transcribir(cliente_mock):
    resultado = MagicMock()
    resultado.text = "hoy hice gym una hora"
    cliente_mock.audio.transcriptions.create.return_value = resultado
    texto = await llm.transcribir(b"ogg-bytes")
    assert texto == "hoy hice gym una hora"
    llamada = cliente_mock.audio.transcriptions.create.call_args
    assert llamada.kwargs["file"] == ("audio.ogg", b"ogg-bytes")
