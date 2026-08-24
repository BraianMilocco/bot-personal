"""Schemas Pydantic de extracción estructurada del LLM."""

from datetime import date, time
from decimal import Decimal
from typing import Literal

from pydantic import BaseModel, field_validator

Momento = Literal["desayuno", "almuerzo", "merienda", "cena", "snack"]
Intensidad = Literal["baja", "media", "alta"]

Intent = Literal[
    "registrar_comida",
    "registrar_actividad",
    "registrar_peso",
    "actualizar_perfil",
    "analizar_examen",
    "consultar",
    "sugerir",
    "otro",
]


class IntentResult(BaseModel):
    intent: Intent


def _a_minuscula(v: str | None) -> str | None:
    return v.strip().lower() if isinstance(v, str) else v


class ComidaExtraida(BaseModel):
    descripcion_normalizada: str
    kcal_est: int | None = None
    proteinas_g: int | None = None
    carbs_g: int | None = None
    grasas_g: int | None = None
    confianza: Literal["alta", "media", "baja"] = "media"
    fecha: date | None = None
    momento: Momento | None = None
    hora_aprox: time | None = None
    necesita_aclaracion: str | None = None  # nombre del campo ambiguo, o None

    _normalizar_momento = field_validator("momento", mode="before")(_a_minuscula)


class ActividadExtraida(BaseModel):
    tipo: str
    duracion_min: int | None = None
    intensidad: Intensidad | None = None
    pasos: int | None = None
    distancia_km: Decimal | None = None
    kcal_est: int | None = None
    fecha: date | None = None
    hora_aprox: time | None = None
    notas: str | None = None
    necesita_aclaracion: str | None = None

    _normalizar_tipo = field_validator("tipo", "intensidad", mode="before")(_a_minuscula)


class PesoExtraido(BaseModel):
    peso_kg: Decimal
    fecha: date | None = None


class PerfilUpdate(BaseModel):
    sexo: str | None = None
    fecha_nac: date | None = None
    altura_cm: int | None = None
    peso_actual_kg: Decimal | None = None
    objetivo: str | None = None
    restricciones: str | None = None
    notas: str | None = None


class ValorExamen(BaseModel):
    nombre: str
    valor: str
    unidad: str | None = None
    ref_min: str | None = None
    ref_max: str | None = None

    _normalizar_nombre = field_validator("nombre", mode="before")(_a_minuscula)


class ExamenExtraido(BaseModel):
    fecha_estudio: date | None = None
    tipo: Literal["sangre", "orina", "otro"] = "otro"
    valores: list[ValorExamen] = []

    _normalizar_tipo = field_validator("tipo", mode="before")(_a_minuscula)


class ClasificacionImagen(BaseModel):
    categoria: Literal["plato", "estudio", "captura_app", "otro"]

    _normalizar = field_validator("categoria", mode="before")(_a_minuscula)
