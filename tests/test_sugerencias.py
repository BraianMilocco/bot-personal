"""DoD 7.1: análisis cruzado con lenguaje de posibilidad; pedidos prohibidos derivan."""

from datetime import date, timedelta
from decimal import Decimal

from app.agent.graph import procesar_mensaje
from app.db import consultas
from app.db import repository as repo
from app.db.session import get_session
from tests.conftest import respuesta_llm

HOY = date.today()
LUNES, _ = consultas.semana_de(HOY)


def _estado(user_id, texto):
    return {
        "telegram_id": 424242,
        "user_id": user_id,
        "nombre": "Test",
        "tz": "America/Argentina/Buenos_Aires",
        "input_text": texto,
        "origen": "texto",
    }


async def _seed_kcal_altas_poca_actividad_peso_sube(user_id):
    async with get_session() as session:
        await repo.upsert_perfil(session, user_id, objetivo="bajar 5kg")
        for i in range(3):
            await repo.crear_comida(
                session,
                user_id,
                fecha=LUNES + timedelta(days=i),
                momento="cena",
                descripcion="pizza",
                origen="texto",
                kcal_est=2600,
                proteinas_g=60,
            )
        await repo.crear_peso(
            session, user_id, fecha=HOY - timedelta(days=7), peso_kg=Decimal("83.00")
        )
        await repo.crear_peso(session, user_id, fecha=HOY, peso_kg=Decimal("83.40"))


async def test_sugerencia_conecta_los_factores(cliente_mock, user_id):
    await _seed_kcal_altas_poca_actividad_peso_sube(user_id)
    cliente_mock.chat.completions.create.side_effect = [
        respuesta_llm('{"intent": "sugerir"}'),
        respuesta_llm(
            "Esta semana promediaste ~2600 kcal/día, no registraste entrenos y tu peso "
            "subió 400g — puede deberse a ese combo. Si el objetivo sigue siendo bajar, "
            "una opción es reforzar caminatas o aflojar con las harinas de la cena."
        ),
    ]
    respuesta = await procesar_mensaje(_estado(user_id, "¿algún consejo para esta semana?"))
    assert "puede deberse a" in respuesta
    assert "una opción es" in respuesta

    # el contexto cruzado real viajó al LLM: kcal, sesiones, objetivo y delta de peso
    system = cliente_mock.chat.completions.create.call_args.kwargs["messages"][0]["content"]
    assert "~2600 kcal/día" in system
    assert "0 sesiones" in system
    assert "objetivo=bajar 5kg" in system
    assert "delta 0.40kg" in system
    # las reglas duras están en el prompt
    assert "Máximo 3 sugerencias" in system
    assert "PROHIBIDO: suplementos con dosis" in system


async def test_pedido_prohibido_deriva(cliente_mock, user_id):
    await _seed_kcal_altas_poca_actividad_peso_sube(user_id)
    cliente_mock.chat.completions.create.side_effect = [
        respuesta_llm('{"intent": "sugerir"}'),
        respuesta_llm(
            "Eso es terreno de tu médico o nutricionista: no puedo indicarte dosis de "
            "creatina. Lo que sí puedo es ayudarte con hábitos de comida y actividad."
        ),
    ]
    respuesta = await procesar_mensaje(_estado(user_id, "¿qué dosis de creatina tomo?"))
    assert "médico" in respuesta or "nutricionista" in respuesta
    assert "dosis" not in respuesta.split("no puedo indicarte")[0]  # no da la indicación
