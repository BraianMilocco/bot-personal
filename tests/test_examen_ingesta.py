"""DoD 6.1: PDF con texto, PDF escaneado y foto de estudio llegan al nodo de extracción."""

from pathlib import Path
from unittest.mock import AsyncMock, MagicMock

import pymupdf as fitz

from app.agent.graph import _despues_de_entrada, _despues_de_vision, procesar_mensaje
from app.bot import handlers
from tests.conftest import respuesta_llm


def _pdf_con_texto() -> bytes:
    doc = fitz.open()
    pagina = doc.new_page()
    pagina.insert_text((72, 72), "Laboratorio: Glucemia 95 mg/dl (70-110). Hemograma normal.")
    return doc.tobytes()


def _pdf_escaneado() -> bytes:
    doc = fitz.open()
    doc.new_page()  # página sin texto (como un escaneo)
    return doc.tobytes()


def test_extraer_pdf_con_texto():
    texto, imagen = handlers.extraer_pdf(_pdf_con_texto())
    assert "Glucemia 95" in texto
    assert imagen is None


def test_extraer_pdf_escaneado_rasteriza():
    texto, imagen = handlers.extraer_pdf(_pdf_escaneado())
    assert texto is None
    assert imagen is not None and len(imagen) > 100  # png en base64


def test_ruteo_al_nodo_examen():
    assert _despues_de_entrada({"pdf_text": "glucemia 95"}) == "examen"
    assert _despues_de_entrada({"es_estudio": True, "image_b64": "x"}) == "examen"
    assert _despues_de_vision({"clasificacion_imagen": "estudio"}) == "examen"


async def test_handler_pdf_manda_estado_correcto(user_id, monkeypatch, tmp_path):
    monkeypatch.chdir(tmp_path)  # data/ del test, no del repo
    procesar = AsyncMock(return_value="ok")
    monkeypatch.setattr(handlers, "procesar_mensaje", procesar)
    monkeypatch.setattr(
        handlers,
        "usuario_autorizado",
        AsyncMock(return_value={"user_id": user_id, "nombre": "Test", "tz": "UTC"}),
    )
    update = MagicMock()
    update.effective_user.id = 424242
    update.message.reply_text = AsyncMock()
    update.message.caption = None
    documento = MagicMock()
    documento.file_size = 1000
    archivo = MagicMock()
    archivo.download_as_bytearray = AsyncMock(return_value=bytearray(_pdf_con_texto()))
    documento.get_file = AsyncMock(return_value=archivo)
    update.message.document = documento

    await handlers.mensaje_pdf(update, None)

    estado = procesar.call_args[0][0]
    assert "Glucemia 95" in estado["pdf_text"]
    assert estado["image_b64"] is None
    # archivo guardado con nombre hasheado en data/examenes/{user_id}/
    ruta = Path(estado["archivo_path"])
    assert ruta.exists()
    assert ruta.parent == Path("data/examenes") / str(user_id)
    assert len(ruta.stem) == 16


EXAMEN_JSON = (
    '{"fecha_estudio": "2026-08-01", "tipo": "sangre",'
    ' "valores": [{"nombre": "glucemia", "valor": "95", "unidad": "mg/dl",'
    ' "ref_min": "70", "ref_max": "110"}]}'
)


async def test_pdf_llega_al_nodo_examen(cliente_mock, user_id, monkeypatch, tmp_path):
    monkeypatch.chdir(tmp_path)
    cliente_mock.chat.completions.create.return_value = respuesta_llm(EXAMEN_JSON)
    respuesta = await procesar_mensaje(
        {
            "telegram_id": 424242,
            "user_id": user_id,
            "nombre": "Test",
            "tz": "UTC",
            "pdf_text": "Glucemia 95 mg/dl (70-110)",
            "origen": "imagen",
        }
    )
    assert "Guardé tu estudio" in respuesta


async def test_foto_estudio_llega_al_nodo_examen(cliente_mock, user_id, monkeypatch, tmp_path):
    monkeypatch.chdir(tmp_path)
    cliente_mock.chat.completions.create.side_effect = [
        respuesta_llm('{"categoria": "estudio"}'),
        respuesta_llm(EXAMEN_JSON),
    ]
    respuesta = await procesar_mensaje(
        {
            "telegram_id": 424242,
            "user_id": user_id,
            "nombre": "Test",
            "tz": "UTC",
            "image_b64": "aW1n",
            "origen": "imagen",
        }
    )
    assert "Guardé tu estudio" in respuesta
