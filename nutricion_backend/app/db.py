"""Conexión a la base de datos, sesión y contexto multi-tenant.

Estrategia multi-tenant: esquema compartido con `tenant_id` en cada tabla y
Row-Level Security (RLS) de Postgres. La app fija el tenant activo por sesión
con `set_config('app.tenant_id', ...)`; las políticas RLS filtran solas por ese
valor, así que ninguna consulta puede ver datos de otro entrenador aunque a
alguien se le olvide un `WHERE`.
"""
from __future__ import annotations

import os
import uuid

from sqlalchemy import ForeignKey, create_engine, text
from sqlalchemy.orm import (
    DeclarativeBase,
    Mapped,
    mapped_column,
    sessionmaker,
    Session,
)


# Carga las variables de .env si el archivo existe, para que cualquier script
# (test_rls, futuros endpoints...) use la misma DATABASE_URL, no solo Alembic.
try:
    from dotenv import load_dotenv
    load_dotenv()
except ImportError:
    pass

DATABASE_URL = os.environ.get(
    "DATABASE_URL", "postgresql+psycopg://localhost/nutricion"
)

# `future=True` es el modo 2.0. pool_pre_ping evita conexiones muertas.
engine = create_engine(DATABASE_URL, pool_pre_ping=True, future=True)
SessionLocal = sessionmaker(bind=engine, expire_on_commit=False, future=True)


class Base(DeclarativeBase):
    """Base declarativa de todos los modelos."""


class TenantScoped:
    """Mixin para tablas que pertenecen a un entrenador (tenant).

    Añade `tenant_id` a cada tabla. Se denormaliza a propósito en TODAS las
    tablas del dominio (aunque el tenant sea deducible por el padre) porque las
    políticas RLS son por tabla y necesitan la columna directa.
    """

    tenant_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("trainer.id", ondelete="CASCADE"), index=True, nullable=False
    )


def set_tenant(session: Session, tenant_id: uuid.UUID | str) -> None:
    """Fija el tenant activo para la conexión de esta sesión.

    Debe llamarse al inicio de cada request, dentro de la transacción, antes de
    tocar cualquier tabla del dominio. `is_local=true` -> el valor se limpia al
    terminar la transacción, así no se filtra entre requests que reusan conexión.

    Solo aplica en PostgreSQL (donde vive el RLS). En otros motores (p. ej.
    SQLite en tests) es un no-op.
    """
    if session.bind is None or session.bind.dialect.name != "postgresql":
        return
    session.execute(
        text("SELECT set_config('app.tenant_id', :tid, true)"),
        {"tid": str(tenant_id)},
    )
