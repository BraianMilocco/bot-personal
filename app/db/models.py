from datetime import date, datetime, time
from decimal import Decimal

from sqlalchemy import (
    JSON,
    BigInteger,
    Boolean,
    CheckConstraint,
    Date,
    DateTime,
    ForeignKey,
    Index,
    Numeric,
    String,
    Text,
    Time,
    UniqueConstraint,
    func,
)
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column


class Base(DeclarativeBase):
    pass


MOMENTOS = ("desayuno", "almuerzo", "merienda", "cena", "snack")
ORIGENES = ("texto", "imagen", "audio")
INTENSIDADES = ("baja", "media", "alta")


class User(Base):
    __tablename__ = "users"

    id: Mapped[int] = mapped_column(primary_key=True)
    telegram_id: Mapped[int] = mapped_column(BigInteger, unique=True, index=True)
    nombre: Mapped[str] = mapped_column(String)
    telefono: Mapped[str | None] = mapped_column(String, nullable=True)
    activo: Mapped[bool] = mapped_column(Boolean, default=True)
    timezone: Mapped[str] = mapped_column(String)


class Perfil(Base):
    __tablename__ = "perfiles"

    user_id: Mapped[int] = mapped_column(ForeignKey("users.id"), primary_key=True)
    sexo: Mapped[str | None] = mapped_column(String, nullable=True)
    fecha_nac: Mapped[date | None] = mapped_column(Date, nullable=True)
    altura_cm: Mapped[int | None] = mapped_column(nullable=True)
    peso_actual_kg: Mapped[Decimal | None] = mapped_column(Numeric(5, 2), nullable=True)
    objetivo: Mapped[str | None] = mapped_column(Text, nullable=True)
    restricciones: Mapped[str | None] = mapped_column(Text, nullable=True)
    notas: Mapped[str | None] = mapped_column(Text, nullable=True)
    actualizado_en: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )


class Peso(Base):
    __tablename__ = "pesos"
    __table_args__ = (Index("ix_pesos_user_fecha", "user_id", "fecha"),)

    id: Mapped[int] = mapped_column(primary_key=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id"))
    fecha: Mapped[date] = mapped_column(Date)
    peso_kg: Mapped[Decimal] = mapped_column(Numeric(5, 2))
    creado_en: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())


class Comida(Base):
    __tablename__ = "comidas"
    __table_args__ = (
        Index("ix_comidas_user_fecha", "user_id", "fecha"),
        CheckConstraint(f"momento IN {MOMENTOS}", name="ck_comidas_momento"),
        CheckConstraint(f"origen IN {ORIGENES}", name="ck_comidas_origen"),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id"))
    fecha: Mapped[date] = mapped_column(Date)
    momento: Mapped[str] = mapped_column(String)
    hora_aprox: Mapped[time | None] = mapped_column(Time, nullable=True)
    descripcion: Mapped[str] = mapped_column(Text)
    origen: Mapped[str] = mapped_column(String)
    kcal_est: Mapped[int | None] = mapped_column(nullable=True)
    proteinas_g: Mapped[int | None] = mapped_column(nullable=True)
    carbs_g: Mapped[int | None] = mapped_column(nullable=True)
    grasas_g: Mapped[int | None] = mapped_column(nullable=True)
    raw_input: Mapped[str | None] = mapped_column(Text, nullable=True)
    creado_en: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())


class Actividad(Base):
    __tablename__ = "actividades"
    __table_args__ = (
        Index("ix_actividades_user_fecha", "user_id", "fecha"),
        CheckConstraint(f"origen IN {ORIGENES}", name="ck_actividades_origen"),
        CheckConstraint(
            f"intensidad IS NULL OR intensidad IN {INTENSIDADES}",
            name="ck_actividades_intensidad",
        ),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id"))
    fecha: Mapped[date] = mapped_column(Date)
    hora_aprox: Mapped[time | None] = mapped_column(Time, nullable=True)
    tipo: Mapped[str] = mapped_column(Text)
    duracion_min: Mapped[int | None] = mapped_column(nullable=True)
    intensidad: Mapped[str | None] = mapped_column(String, nullable=True)
    pasos: Mapped[int | None] = mapped_column(nullable=True)
    distancia_km: Mapped[Decimal | None] = mapped_column(Numeric(6, 2), nullable=True)
    kcal_est: Mapped[int | None] = mapped_column(nullable=True)
    origen: Mapped[str] = mapped_column(String)
    notas: Mapped[str | None] = mapped_column(Text, nullable=True)
    raw_input: Mapped[str | None] = mapped_column(Text, nullable=True)
    creado_en: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())


class MetricasDia(Base):
    __tablename__ = "metricas_dia"
    __table_args__ = (UniqueConstraint("user_id", "fecha", name="uq_metricas_dia_user_fecha"),)

    id: Mapped[int] = mapped_column(primary_key=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id"))
    fecha: Mapped[date] = mapped_column(Date)
    pasos_total: Mapped[int | None] = mapped_column(nullable=True)
    fuente: Mapped[str | None] = mapped_column(Text, nullable=True)


class RegistroPendiente(Base):
    """Registro a medio guardar esperando UNA aclaración del usuario (uno por user)."""

    __tablename__ = "registros_pendientes"

    user_id: Mapped[int] = mapped_column(ForeignKey("users.id"), primary_key=True)
    tipo: Mapped[str] = mapped_column(String)  # 'comida' | 'actividad' | ...
    payload: Mapped[dict] = mapped_column(JSON)
    campo: Mapped[str] = mapped_column(String)
    pregunta: Mapped[str] = mapped_column(Text)
    creado_en: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())


class Examen(Base):
    __tablename__ = "examenes"
    __table_args__ = (Index("ix_examenes_user_fecha", "user_id", "fecha_estudio"),)

    id: Mapped[int] = mapped_column(primary_key=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id"))
    fecha_estudio: Mapped[date] = mapped_column(Date)
    tipo: Mapped[str] = mapped_column(Text)
    archivo_path: Mapped[str | None] = mapped_column(Text, nullable=True)
    resumen: Mapped[str | None] = mapped_column(Text, nullable=True)
    creado_en: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())


class ExamenValor(Base):
    __tablename__ = "examen_valores"

    id: Mapped[int] = mapped_column(primary_key=True)
    examen_id: Mapped[int] = mapped_column(ForeignKey("examenes.id"), index=True)
    nombre: Mapped[str] = mapped_column(Text)
    valor: Mapped[str] = mapped_column(Text)
    unidad: Mapped[str | None] = mapped_column(Text, nullable=True)
    ref_min: Mapped[str | None] = mapped_column(Text, nullable=True)
    ref_max: Mapped[str | None] = mapped_column(Text, nullable=True)
    fuera_de_rango: Mapped[bool | None] = mapped_column(Boolean, nullable=True)


class ConversacionMensaje(Base):
    __tablename__ = "conversacion_mensajes"
    __table_args__ = (
        Index("ix_conversacion_user_creado", "user_id", "creado_en"),
        CheckConstraint("rol IN ('user', 'assistant')", name="ck_conversacion_rol"),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id"))
    rol: Mapped[str] = mapped_column(String)
    contenido: Mapped[str] = mapped_column(Text)
    creado_en: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
