"""Nutrición inicial: tablas + Row-Level Security multi-tenant.

Revision ID: 0001_nutrition
Revises:
Create Date: 2026-09-07
"""
from __future__ import annotations

import sqlalchemy as sa
from alembic import op

revision = "0001_nutrition"
down_revision = None
branch_labels = None
depends_on = None

# Todas las tablas del dominio llevan tenant_id y se aíslan por RLS.
# `trainer` NO lleva RLS: el login/alta ocurren antes de conocer el tenant.
TENANT_TABLES = [
    "cliente",
    "alimento",
    "receta",
    "receta_ingrediente",
    "dieta",
    "dieta_dia",
    "comida",
    "comida_opcion",
    "opcion_ingrediente",
]


def _uuid_pk() -> sa.Column:
    return sa.Column(
        "id",
        sa.Uuid(as_uuid=True),
        primary_key=True,
        server_default=sa.text("gen_random_uuid()"),
    )


def _tenant_fk() -> sa.Column:
    return sa.Column(
        "tenant_id",
        sa.Uuid(as_uuid=True),
        sa.ForeignKey("trainer.id", ondelete="CASCADE"),
        nullable=False,
    )


def upgrade() -> None:
    # gen_random_uuid() vive en pgcrypto (built-in desde PG13, pero la extensión
    # asegura compatibilidad).
    op.execute("CREATE EXTENSION IF NOT EXISTS pgcrypto")

    op.create_table(
        "trainer",
        _uuid_pk(),
        sa.Column("nombre", sa.String(120), nullable=False),
        sa.Column("email", sa.String(255), nullable=False, unique=True),
        sa.Column("created_at", sa.DateTime(timezone=True),
                  server_default=sa.text("now()"), nullable=False),
    )

    op.create_table(
        "cliente",
        _uuid_pk(),
        _tenant_fk(),
        sa.Column("nombre", sa.String(120), nullable=False),
        sa.Column("objetivo", sa.String(120)),
        sa.Column("created_at", sa.DateTime(timezone=True),
                  server_default=sa.text("now()"), nullable=False),
    )

    op.create_table(
        "alimento",
        _uuid_pk(),
        _tenant_fk(),
        sa.Column("nombre", sa.String(160), nullable=False),
        sa.Column("tipo", sa.String(10), nullable=False, server_default="peso"),
        sa.Column("kcal", sa.Float, nullable=False),
        sa.Column("prote", sa.Float, nullable=False),
        sa.Column("carbs", sa.Float, nullable=False),
        sa.Column("grasa", sa.Float, nullable=False),
        sa.Column("g_por_unidad", sa.Float),
        sa.Column("created_at", sa.DateTime(timezone=True),
                  server_default=sa.text("now()"), nullable=False),
        sa.CheckConstraint("tipo in ('peso', 'unidad')", name="ck_alimento_tipo"),
    )

    op.create_table(
        "receta",
        _uuid_pk(),
        _tenant_fk(),
        sa.Column("nombre", sa.String(160), nullable=False),
        sa.Column("foto_url", sa.String(500)),
        sa.Column("instrucciones", sa.Text),
        sa.Column("created_at", sa.DateTime(timezone=True),
                  server_default=sa.text("now()"), nullable=False),
    )

    op.create_table(
        "receta_ingrediente",
        _uuid_pk(),
        _tenant_fk(),
        sa.Column("receta_id", sa.Uuid(as_uuid=True),
                  sa.ForeignKey("receta.id", ondelete="CASCADE"), nullable=False),
        sa.Column("alimento_id", sa.Uuid(as_uuid=True),
                  sa.ForeignKey("alimento.id", ondelete="RESTRICT"), nullable=False),
        sa.Column("cantidad_base", sa.Float, nullable=False),
        sa.Column("fijo", sa.Boolean, nullable=False, server_default=sa.false()),
        sa.Column("min_qty", sa.Float, nullable=False, server_default="0"),
        sa.Column("max_qty", sa.Float),
    )

    op.create_table(
        "dieta",
        _uuid_pk(),
        _tenant_fk(),
        sa.Column("cliente_id", sa.Uuid(as_uuid=True),
                  sa.ForeignKey("cliente.id", ondelete="CASCADE")),
        sa.Column("nombre", sa.String(160), nullable=False),
        sa.Column("es_plantilla", sa.Boolean, nullable=False,
                  server_default=sa.false()),
        sa.Column("created_at", sa.DateTime(timezone=True),
                  server_default=sa.text("now()"), nullable=False),
    )

    op.create_table(
        "dieta_dia",
        _uuid_pk(),
        _tenant_fk(),
        sa.Column("dieta_id", sa.Uuid(as_uuid=True),
                  sa.ForeignKey("dieta.id", ondelete="CASCADE"), nullable=False),
        sa.Column("etiqueta", sa.String(60), nullable=False),
        sa.Column("orden", sa.Integer, nullable=False, server_default="0"),
        sa.Column("obj_kcal", sa.Float),
        sa.Column("obj_prote", sa.Float),
        sa.Column("obj_carbs", sa.Float),
        sa.Column("obj_grasa", sa.Float),
    )

    op.create_table(
        "comida",
        _uuid_pk(),
        _tenant_fk(),
        sa.Column("dieta_dia_id", sa.Uuid(as_uuid=True),
                  sa.ForeignKey("dieta_dia.id", ondelete="CASCADE"), nullable=False),
        sa.Column("nombre", sa.String(80), nullable=False),
        sa.Column("orden", sa.Integer, nullable=False, server_default="0"),
        sa.Column("obj_kcal", sa.Float, nullable=False),
        sa.Column("obj_prote", sa.Float, nullable=False),
        sa.Column("obj_carbs", sa.Float, nullable=False),
        sa.Column("obj_grasa", sa.Float, nullable=False),
    )

    op.create_table(
        "comida_opcion",
        _uuid_pk(),
        _tenant_fk(),
        sa.Column("comida_id", sa.Uuid(as_uuid=True),
                  sa.ForeignKey("comida.id", ondelete="CASCADE"), nullable=False),
        sa.Column("receta_id", sa.Uuid(as_uuid=True),
                  sa.ForeignKey("receta.id", ondelete="SET NULL")),
        sa.Column("orden", sa.Integer, nullable=False, server_default="0"),
        sa.Column("por_defecto", sa.Boolean, nullable=False,
                  server_default=sa.false()),
        sa.Column("res_kcal", sa.Float),
        sa.Column("res_prote", sa.Float),
        sa.Column("res_carbs", sa.Float),
        sa.Column("res_grasa", sa.Float),
    )

    op.create_table(
        "opcion_ingrediente",
        _uuid_pk(),
        _tenant_fk(),
        sa.Column("opcion_id", sa.Uuid(as_uuid=True),
                  sa.ForeignKey("comida_opcion.id", ondelete="CASCADE"),
                  nullable=False),
        sa.Column("alimento_id", sa.Uuid(as_uuid=True),
                  sa.ForeignKey("alimento.id", ondelete="RESTRICT"), nullable=False),
        sa.Column("cantidad", sa.Float, nullable=False),
        sa.Column("fijo", sa.Boolean, nullable=False, server_default=sa.false()),
        sa.Column("min_qty", sa.Float, nullable=False, server_default="0"),
        sa.Column("max_qty", sa.Float),
    )

    # Índices por tenant_id (las políticas RLS filtran por esta columna).
    for table in TENANT_TABLES:
        op.create_index(f"ix_{table}_tenant_id", table, ["tenant_id"])

    # --- Row-Level Security -------------------------------------------------
    # Cada tabla solo deja ver/insertar/modificar filas de su tenant activo.
    # FORCE aplica la política también al dueño de la tabla (la app se conecta
    # como dueño). Si 'app.tenant_id' no está fijado, no se ve ninguna fila.
    for table in TENANT_TABLES:
        op.execute(f"ALTER TABLE {table} ENABLE ROW LEVEL SECURITY")
        op.execute(f"ALTER TABLE {table} FORCE ROW LEVEL SECURITY")
        op.execute(
            f"CREATE POLICY tenant_isolation ON {table} "
            f"USING (tenant_id = NULLIF(current_setting('app.tenant_id', true), '')::uuid) "
            f"WITH CHECK (tenant_id = NULLIF(current_setting('app.tenant_id', true), '')::uuid)"
        )


def downgrade() -> None:
    for table in TENANT_TABLES:
        op.execute(f"DROP POLICY IF EXISTS tenant_isolation ON {table}")

    op.drop_table("opcion_ingrediente")
    op.drop_table("comida_opcion")
    op.drop_table("comida")
    op.drop_table("dieta_dia")
    op.drop_table("dieta")
    op.drop_table("receta_ingrediente")
    op.drop_table("receta")
    op.drop_table("alimento")
    op.drop_table("cliente")
    op.drop_table("trainer")