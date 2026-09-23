"""Modelos del dominio de nutrición.

Dos lados:
  - Biblioteca (reutilizable): Alimento, Receta (+ RecetaIngrediente).
  - Plan asignado (lo que ve el cliente): Dieta -> DietaDia -> Comida ->
    ComidaOpcion (+ OpcionIngrediente).

Al meter una receta en una comida se INSTANCIA: sus ingredientes se copian a
OpcionIngrediente y el motor de macros ajusta ahí las cantidades. Editar la
receta de biblioteca después NO altera las dietas ya asignadas.
"""
from __future__ import annotations

import uuid
from datetime import datetime, timezone

from sqlalchemy import (
    Boolean,
    CheckConstraint,
    DateTime,
    Float,
    ForeignKey,
    Integer,
    String,
    Text,
    Uuid,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from .db import Base, TenantScoped


def _uuid_pk() -> Mapped[uuid.UUID]:
    return mapped_column(Uuid(as_uuid=True), primary_key=True, default=uuid.uuid4)


def _now() -> datetime:
    return datetime.now(timezone.utc)


class Trainer(Base):
    """El profesional. Es el 'tenant': cada entrenador aísla sus datos."""
    __tablename__ = "trainer"

    id: Mapped[uuid.UUID] = _uuid_pk()
    nombre: Mapped[str] = mapped_column(String(120), nullable=False)
    email: Mapped[str] = mapped_column(String(255), unique=True, nullable=False)
    password_hash: Mapped[str] = mapped_column(String(255), nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=_now, nullable=False
    )


class Cliente(Base, TenantScoped):
    __tablename__ = "cliente"

    id: Mapped[uuid.UUID] = _uuid_pk()
    nombre: Mapped[str] = mapped_column(String(120), nullable=False)
    objetivo: Mapped[str | None] = mapped_column(String(120))
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=_now, nullable=False
    )

    dietas: Mapped[list["Dieta"]] = relationship(
        back_populates="cliente", passive_deletes=True
    )


class Alimento(Base, TenantScoped):
    """Alimento de la base de datos del entrenador.

    tipo='peso'   -> los macros son POR 100 g (la cantidad se mide en gramos).
    tipo='unidad' -> los macros son POR 1 UNIDAD (la cantidad va en enteros).
    """
    __tablename__ = "alimento"
    __table_args__ = (
        CheckConstraint("tipo in ('peso', 'unidad')", name="ck_alimento_tipo"),
    )

    id: Mapped[uuid.UUID] = _uuid_pk()
    nombre: Mapped[str] = mapped_column(String(160), nullable=False)
    tipo: Mapped[str] = mapped_column(String(10), nullable=False, default="peso")
    kcal: Mapped[float] = mapped_column(Float, nullable=False)
    prote: Mapped[float] = mapped_column(Float, nullable=False)
    carbs: Mapped[float] = mapped_column(Float, nullable=False)
    grasa: Mapped[float] = mapped_column(Float, nullable=False)
    # Solo para tipo='unidad': cuántos gramos pesa una unidad (informativo).
    g_por_unidad: Mapped[float | None] = mapped_column(Float)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=_now, nullable=False
    )


class Receta(Base, TenantScoped):
    __tablename__ = "receta"

    id: Mapped[uuid.UUID] = _uuid_pk()
    nombre: Mapped[str] = mapped_column(String(160), nullable=False)
    foto_url: Mapped[str | None] = mapped_column(String(500))
    instrucciones: Mapped[str | None] = mapped_column(Text)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=_now, nullable=False
    )

    ingredientes: Mapped[list["RecetaIngrediente"]] = relationship(
        back_populates="receta",
        cascade="all, delete-orphan",
        passive_deletes=True,
    )


class RecetaIngrediente(Base, TenantScoped):
    """Línea de una receta de biblioteca: qué alimento y en qué cantidad base."""
    __tablename__ = "receta_ingrediente"

    id: Mapped[uuid.UUID] = _uuid_pk()
    receta_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("receta.id", ondelete="CASCADE"), nullable=False, index=True
    )
    alimento_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("alimento.id", ondelete="RESTRICT"), nullable=False
    )
    cantidad_base: Mapped[float] = mapped_column(Float, nullable=False)
    fijo: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    min_qty: Mapped[float] = mapped_column(Float, nullable=False, default=0.0)
    max_qty: Mapped[float | None] = mapped_column(Float)

    receta: Mapped["Receta"] = relationship(back_populates="ingredientes")
    alimento: Mapped["Alimento"] = relationship()


class Dieta(Base, TenantScoped):
    """Plan nutricional. cliente_id nulo + es_plantilla=True -> plantilla."""
    __tablename__ = "dieta"

    id: Mapped[uuid.UUID] = _uuid_pk()
    cliente_id: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("cliente.id", ondelete="CASCADE"), index=True
    )
    nombre: Mapped[str] = mapped_column(String(160), nullable=False)
    es_plantilla: Mapped[bool] = mapped_column(
        Boolean, nullable=False, default=False
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=_now, nullable=False
    )

    cliente: Mapped["Cliente | None"] = relationship(back_populates="dietas")
    dias: Mapped[list["DietaDia"]] = relationship(
        back_populates="dieta",
        cascade="all, delete-orphan",
        passive_deletes=True,
        order_by="DietaDia.orden",
    )


class DietaDia(Base, TenantScoped):
    __tablename__ = "dieta_dia"

    id: Mapped[uuid.UUID] = _uuid_pk()
    dieta_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("dieta.id", ondelete="CASCADE"), nullable=False, index=True
    )
    etiqueta: Mapped[str] = mapped_column(String(60), nullable=False)
    orden: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    # Objetivo del día (opcional): el cliente quiere ver el total del día y
    # además poder ajustar por comida. La fuente de verdad para el motor son
    # los objetivos de cada COMIDA; esto es la guía/visión del día.
    obj_kcal: Mapped[float | None] = mapped_column(Float)
    obj_prote: Mapped[float | None] = mapped_column(Float)
    obj_carbs: Mapped[float | None] = mapped_column(Float)
    obj_grasa: Mapped[float | None] = mapped_column(Float)

    dieta: Mapped["Dieta"] = relationship(back_populates="dias")
    comidas: Mapped[list["Comida"]] = relationship(
        back_populates="dia",
        cascade="all, delete-orphan",
        passive_deletes=True,
        order_by="Comida.orden",
    )


class Comida(Base, TenantScoped):
    """Una comida del día con sus OBJETIVOS de macros (los usa el motor)."""
    __tablename__ = "comida"

    id: Mapped[uuid.UUID] = _uuid_pk()
    dieta_dia_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("dieta_dia.id", ondelete="CASCADE"), nullable=False, index=True
    )
    nombre: Mapped[str] = mapped_column(String(80), nullable=False)
    orden: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    obj_kcal: Mapped[float] = mapped_column(Float, nullable=False)
    obj_prote: Mapped[float] = mapped_column(Float, nullable=False)
    obj_carbs: Mapped[float] = mapped_column(Float, nullable=False)
    obj_grasa: Mapped[float] = mapped_column(Float, nullable=False)

    dia: Mapped["DietaDia"] = relationship(back_populates="comidas")
    opciones: Mapped[list["ComidaOpcion"]] = relationship(
        back_populates="comida",
        cascade="all, delete-orphan",
        passive_deletes=True,
        order_by="ComidaOpcion.orden",
    )


class ComidaOpcion(Base, TenantScoped):
    """Una opción de una comida (una receta ya instanciada y ajustada).

    receta_id es solo el ORIGEN del que se copió; los ingredientes reales y
    ajustados viven en OpcionIngrediente. res_* son los macros conseguidos tras
    el ajuste (cache para que la app del cliente no recalcule).
    """
    __tablename__ = "comida_opcion"

    id: Mapped[uuid.UUID] = _uuid_pk()
    comida_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("comida.id", ondelete="CASCADE"), nullable=False, index=True
    )
    receta_id: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("receta.id", ondelete="SET NULL")
    )
    orden: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    por_defecto: Mapped[bool] = mapped_column(
        Boolean, nullable=False, default=False
    )
    res_kcal: Mapped[float | None] = mapped_column(Float)
    res_prote: Mapped[float | None] = mapped_column(Float)
    res_carbs: Mapped[float | None] = mapped_column(Float)
    res_grasa: Mapped[float | None] = mapped_column(Float)

    comida: Mapped["Comida"] = relationship(back_populates="opciones")
    ingredientes: Mapped[list["OpcionIngrediente"]] = relationship(
        back_populates="opcion",
        cascade="all, delete-orphan",
        passive_deletes=True,
    )


class OpcionIngrediente(Base, TenantScoped):
    """Línea real de una opción de comida, con la cantidad ya ajustada."""
    __tablename__ = "opcion_ingrediente"

    id: Mapped[uuid.UUID] = _uuid_pk()
    opcion_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("comida_opcion.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    alimento_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("alimento.id", ondelete="RESTRICT"), nullable=False
    )
    cantidad: Mapped[float] = mapped_column(Float, nullable=False)
    fijo: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    min_qty: Mapped[float] = mapped_column(Float, nullable=False, default=0.0)
    max_qty: Mapped[float | None] = mapped_column(Float)

    opcion: Mapped["ComidaOpcion"] = relationship(back_populates="ingredientes")
    alimento: Mapped["Alimento"] = relationship()
