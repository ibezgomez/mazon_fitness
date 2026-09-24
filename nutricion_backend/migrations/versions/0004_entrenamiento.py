"""Entrenamiento: ejercicios, rutinas, días y ejercicios de rutina + RLS.

Revision ID: 0004_entrenamiento
Revises: 0003_trainer_password
Create Date: 2026-09-24
"""
from __future__ import annotations

import sqlalchemy as sa
from alembic import op

revision = "0004_entrenamiento"
down_revision = "0003_trainer_password"
branch_labels = None
depends_on = None

TENANT_TABLES = ["ejercicio", "rutina", "rutina_dia", "rutina_ejercicio"]


def _uuid_pk() -> sa.Column:
    return sa.Column("id", sa.Uuid(as_uuid=True), primary_key=True,
                     server_default=sa.text("gen_random_uuid()"))


def _tenant_fk() -> sa.Column:
    return sa.Column("tenant_id", sa.Uuid(as_uuid=True),
                     sa.ForeignKey("trainer.id", ondelete="CASCADE"), nullable=False)


def upgrade() -> None:
    op.create_table(
        "ejercicio",
        _uuid_pk(), _tenant_fk(),
        sa.Column("nombre", sa.String(160), nullable=False),
        sa.Column("grupo_muscular", sa.String(80)),
        sa.Column("video_url", sa.String(500)),
        sa.Column("notas", sa.Text),
        sa.Column("created_at", sa.DateTime(timezone=True),
                  server_default=sa.text("now()"), nullable=False),
    )
    op.create_table(
        "rutina",
        _uuid_pk(), _tenant_fk(),
        sa.Column("cliente_id", sa.Uuid(as_uuid=True),
                  sa.ForeignKey("cliente.id", ondelete="CASCADE")),
        sa.Column("nombre", sa.String(160), nullable=False),
        sa.Column("es_plantilla", sa.Boolean, nullable=False, server_default=sa.false()),
        sa.Column("created_at", sa.DateTime(timezone=True),
                  server_default=sa.text("now()"), nullable=False),
    )
    op.create_table(
        "rutina_dia",
        _uuid_pk(), _tenant_fk(),
        sa.Column("rutina_id", sa.Uuid(as_uuid=True),
                  sa.ForeignKey("rutina.id", ondelete="CASCADE"), nullable=False),
        sa.Column("etiqueta", sa.String(80), nullable=False),
        sa.Column("orden", sa.Integer, nullable=False, server_default="0"),
    )
    op.create_table(
        "rutina_ejercicio",
        _uuid_pk(), _tenant_fk(),
        sa.Column("rutina_dia_id", sa.Uuid(as_uuid=True),
                  sa.ForeignKey("rutina_dia.id", ondelete="CASCADE"), nullable=False),
        sa.Column("ejercicio_id", sa.Uuid(as_uuid=True),
                  sa.ForeignKey("ejercicio.id", ondelete="RESTRICT"), nullable=False),
        sa.Column("orden", sa.Integer, nullable=False, server_default="0"),
        sa.Column("series", sa.Integer, nullable=False, server_default="3"),
        sa.Column("reps", sa.String(40), nullable=False, server_default=""),
        sa.Column("descanso_seg", sa.Integer),
        sa.Column("rir", sa.String(20)),
        sa.Column("peso_objetivo", sa.Float),
        sa.Column("notas", sa.Text),
    )

    for table in TENANT_TABLES:
        op.create_index(f"ix_{table}_tenant_id", table, ["tenant_id"])
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
    op.drop_table("rutina_ejercicio")
    op.drop_table("rutina_dia")
    op.drop_table("rutina")
    op.drop_table("ejercicio")
