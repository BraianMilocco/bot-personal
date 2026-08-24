"""Factory de cliente LLM, transcripción de audio y structured output."""

import logging

from openai import AsyncOpenAI
from pydantic import BaseModel, ValidationError

from app.config import settings

logger = logging.getLogger(__name__)

_client: AsyncOpenAI | None = None


def get_client() -> AsyncOpenAI:
    global _client
    if _client is None:
        _client = AsyncOpenAI(api_key=settings.llm_api_key, base_url=settings.llm_base_url)
    return _client


async def transcribir(audio_bytes: bytes, filename: str = "audio.ogg") -> str:
    """Transcribe un audio con el AUDIO_MODEL y devuelve el texto."""
    respuesta = await get_client().audio.transcriptions.create(
        model=settings.audio_model, file=(filename, audio_bytes)
    )
    return respuesta.text


def _log_tokens(respuesta, modelo: str) -> None:
    uso = getattr(respuesta, "usage", None)
    if uso is not None:
        logger.info(
            "llm_tokens modelo=%s prompt=%s completion=%s total=%s",
            modelo,
            getattr(uso, "prompt_tokens", "?"),
            getattr(uso, "completion_tokens", "?"),
            getattr(uso, "total_tokens", "?"),
        )


async def conversar(
    messages: list[dict], *, tools: list[dict] | None = None, model: str | None = None
):
    """Call de chat libre (con tool-calling opcional). Devuelve la respuesta cruda."""
    kwargs = {"tools": tools} if tools else {}
    modelo = model or settings.llm_model
    respuesta = await get_client().chat.completions.create(
        model=modelo, messages=messages, **kwargs
    )
    _log_tokens(respuesta, modelo)
    return respuesta


async def extraer[T: BaseModel](
    schema: type[T], messages: list[dict], *, model: str | None = None
) -> T:
    """Structured output: json_schema + validación Pydantic + 1 retry ante inválido."""
    client = get_client()
    for intento in range(2):
        respuesta = await client.chat.completions.create(
            model=model or settings.llm_model,
            messages=messages,
            response_format={
                "type": "json_schema",
                "json_schema": {"name": schema.__name__, "schema": schema.model_json_schema()},
            },
        )
        _log_tokens(respuesta, model or settings.llm_model)
        contenido = respuesta.choices[0].message.content
        try:
            return schema.model_validate_json(contenido)
        except ValidationError:
            if intento == 1:
                raise
            logger.warning("extraer: JSON inválido para %s, reintentando", schema.__name__)
            messages = [
                *messages,
                {"role": "assistant", "content": contenido},
                {
                    "role": "user",
                    "content": "La respuesta no cumple el schema. Respondé SOLO el JSON válido.",
                },
            ]
    raise AssertionError("inalcanzable")
