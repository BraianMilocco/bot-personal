"""Persistencia de archivos de exámenes (fuera de git, nombre hasheado)."""

import hashlib
from pathlib import Path


def guardar_archivo_examen(user_id: int, contenido: bytes, extension: str) -> str:
    carpeta = Path("data/examenes") / str(user_id)
    carpeta.mkdir(parents=True, exist_ok=True)
    nombre = hashlib.sha256(contenido).hexdigest()[:16] + extension
    ruta = carpeta / nombre
    ruta.write_bytes(contenido)
    return str(ruta)
