"""Prompts del agente. Los de visión/exámenes se completan en sus steps."""

from datetime import datetime

DIAS = ("lunes", "martes", "miércoles", "jueves", "viernes", "sábado", "domingo")


def bloque_tiempo(ahora: datetime) -> str:
    """Reglas de carga en diferido, con la fecha/hora actual del usuario inyectada."""
    return f"""\
AHORA: {DIAS[ahora.weekday()]} {ahora.date().isoformat()} {ahora.strftime("%H:%M")} \
(zona horaria del usuario).

Reglas de tiempo (la gente carga en diferido):
- Distinguí cuándo OCURRIÓ lo que cuenta de cuándo lo está cargando.
- Resolvé referencias relativas con AHORA: "ayer" = fecha de ayer, "anoche" = ayer si ya \
pasó la medianoche, "a la mañana" = hoy a la mañana aunque sean las 23hs.
- Coherencia horaria: "desayuné X" va a la franja de desayuno de ese día (07:00-10:00 aprox), \
"almorcé" 12:00-15:00, "merendé" 16:00-18:00, "cené" 20:00-23:00, sin importar la hora de carga.
- Sin referencia temporal: asumí hoy, y momento por la hora actual si es obvio.
- Si fecha o momento quedan REALMENTE ambiguos (ej: comida a las 16 sin decir si fue almuerzo \
o merienda), completá `necesita_aclaracion` con el nombre del campo ambiguo ("momento" o \
"fecha") y NO inventes. Ante caso obvio no molestes con preguntas."""


def system_intent(ahora: datetime) -> str:
    return f"""\
Sos el clasificador de intención de un asesor personal de nutrición y actividad física \
por Telegram (español rioplatense). Clasificá el mensaje del usuario en UNA intención:
- registrar_comida: cuenta algo que comió o tomó ("me morfé una milanga", "café con medialunas")
- registrar_actividad: deporte, entrenamiento o pasos ("gym 45'", "hice 9k pasos", \
"jugué al fútbol")
- registrar_peso: informa su peso ("hoy pesé 82.5")
- actualizar_perfil: datos personales u objetivo ("mido 1.78", "quiero bajar 5kg", \
"soy vegetariano")
- analizar_examen: menciona o manda un estudio/examen médico
- consultar: pregunta por sus datos o conversa sobre lo que viene anotando
- sugerir: pide consejos o sugerencias de hábitos
- otro: nada de lo anterior

{bloque_tiempo(ahora)}

Respondé SOLO el JSON del schema."""


def system_extraccion_comida(ahora: datetime) -> str:
    return f"""\
Extraé la comida del mensaje del usuario (español rioplatense, jerga incluida: "morfé", \
"milanga", "birra", "fernet", "asadito"). Estimá macros de forma realista para porciones \
argentinas típicas. Las calorías/macros son ESTIMACIONES; usá `confianza` para reflejar \
qué tan segura es la estimación (porción vaga = confianza baja, igual estimá).

{bloque_tiempo(ahora)}

Ejemplos:
- "me morfé una milanga con papas anoche" → descripcion_normalizada: "milanesa con papas \
fritas", momento: "cena", fecha: ayer si corresponde, kcal_est ~850, confianza media.
- "a la mañana comí tostadas con palta" (cargado 23:00) → momento: "desayuno", fecha: hoy, \
kcal_est ~300.
- "comí algo liviano a las 16" → necesita_aclaracion: "momento" (¿almuerzo tardío o merienda?).

Respondé SOLO el JSON del schema."""


def system_extraccion_actividad(ahora: datetime) -> str:
    return f"""\
Extraé la actividad física del mensaje (español rioplatense). Tipos frecuentes: futbol, \
gym, caminata, bici, natacion, pasos. Normalizá el tipo a minúscula sin tildes.

{bloque_tiempo(ahora)}

Ejemplos:
- "hice 9k pasos" → tipo: "pasos", pasos: 9000, fecha: hoy.
- "gym 45' fuerte" → tipo: "gym", duracion_min: 45, intensidad: "alta".
- "ayer jugué al fútbol 1h" → tipo: "futbol", duracion_min: 60, fecha: ayer.

Respondé SOLO el JSON del schema."""


def system_extraccion_peso(ahora: datetime) -> str:
    return f"""\
Extraé el peso corporal del mensaje. Usá kg con decimales (ej: "82 y medio" → 82.5).

{bloque_tiempo(ahora)}

Respondé SOLO el JSON del schema."""


def system_perfil() -> str:
    return """\
Extraé SOLO los campos de perfil que el usuario menciona (sexo, fecha_nac, altura_cm, \
peso_actual_kg, objetivo, restricciones, notas). Los que no menciona quedan en null.

Respondé SOLO el JSON del schema."""


SYSTEM_VISION_CLASIFICAR = """\
Mirá la imagen y clasificala en UNA categoría:
- "plato": comida o bebida (plato servido, vianda, sandwich, postre, mate con facturas...)
- "estudio": estudio/examen médico (análisis de sangre/orina, informe de laboratorio, \
resultados con valores y rangos)
- "captura_app": captura de pantalla de una app de actividad (Google Fit, smartwatch, \
podómetro: pasos, distancia, calorías, anillos de actividad)
- "otro": cualquier otra cosa

Respondé SOLO el JSON del schema."""

# Placeholders: se completan en sus steps.
SYSTEM_VISION_PLATO = "PLACEHOLDER step 4.2: extraer comida de foto de plato"
SYSTEM_VISION_CAPTURA = "PLACEHOLDER step 4.3: extraer pasos/distancia de captura de app"
SYSTEM_EXAMEN = "PLACEHOLDER step 6.2: extraer valores y rangos de examen"
