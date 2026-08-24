"""seed allowed users

Revision ID: c1aaf360f1d2
Revises: e461a656d9be
Create Date: 2026-08-24 20:14:25.680130

Migración de datos: inserta los usuarios de ALLOWED_USERS (env) que no estén en la
db. Idempotente (ON CONFLICT DO NOTHING); no pisa nombres/teléfonos ya editados.
"""

from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op
from app.config import settings

revision: str = "c1aaf360f1d2"
down_revision: str | Sequence[str] | None = "e461a656d9be"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    conn = op.get_bind()
    for u in settings.usuarios_permitidos:
        conn.execute(
            sa.text(
                "INSERT INTO users (telegram_id, nombre, telefono, activo, timezone) "
                "VALUES (:telegram_id, :nombre, :telefono, true, :tz) "
                "ON CONFLICT (telegram_id) DO NOTHING"
            ),
            {
                "telegram_id": u.telegram_id,
                "nombre": u.nombre,
                "telefono": u.telefono,
                "tz": settings.tz,
            },
        )


def downgrade() -> None:
    # seed de datos: no se borran usuarios al bajar
    pass
