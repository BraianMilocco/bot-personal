from datetime import date, time
from decimal import Decimal

import pytest
from pydantic import ValidationError

from app.schemas import (
    ActividadExtraida,
    ClasificacionImagen,
    ComidaExtraida,
    ExamenExtraido,
    PesoExtraido,
)


def test_comida_normaliza_momento_a_minuscula():
    comida = ComidaExtraida(descripcion_normalizada="milanesa", momento="Almuerzo")
    assert comida.momento == "almuerzo"


def test_comida_momento_invalido_da_error_claro():
    with pytest.raises(ValidationError) as excinfo:
        ComidaExtraida(descripcion_normalizada="milanesa", momento="brunch")
    assert "momento" in str(excinfo.value)


def test_comida_con_tiempos_y_aclaracion():
    comida = ComidaExtraida(
        descripcion_normalizada="tostadas con palta",
        fecha=date(2026, 8, 24),
        momento="desayuno",
        hora_aprox=time(8, 30),
        necesita_aclaracion=None,
    )
    assert comida.fecha.isoformat() == "2026-08-24"
    ambigua = ComidaExtraida(descripcion_normalizada="algo", necesita_aclaracion="momento")
    assert ambigua.necesita_aclaracion == "momento"


def test_actividad_normaliza_y_usa_decimal():
    actividad = ActividadExtraida(tipo="Caminata", distancia_km="5.20", intensidad="MEDIA")
    assert actividad.tipo == "caminata"
    assert actividad.intensidad == "media"
    assert actividad.distancia_km == Decimal("5.20")
    assert isinstance(actividad.distancia_km, Decimal)


def test_actividad_intensidad_invalida():
    with pytest.raises(ValidationError):
        ActividadExtraida(tipo="gym", intensidad="brutal")


def test_peso_decimal():
    peso = PesoExtraido(peso_kg="82.5")
    assert peso.peso_kg == Decimal("82.5")


def test_examen_valores_normalizados():
    examen = ExamenExtraido(
        tipo="Sangre",
        valores=[{"nombre": "Glucemia", "valor": "<5", "ref_min": "70", "ref_max": "110"}],
    )
    assert examen.tipo == "sangre"
    assert examen.valores[0].nombre == "glucemia"
    assert examen.valores[0].valor == "<5"  # el valor crudo no se toca


def test_clasificacion_imagen():
    assert ClasificacionImagen(categoria="PLATO").categoria == "plato"
    with pytest.raises(ValidationError):
        ClasificacionImagen(categoria="selfie")
