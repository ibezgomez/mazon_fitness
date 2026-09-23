"""Blinda las políticas RLS: trata la cadena vacía como 'sin tenant'.

Cuando una conexión se reutiliza y no se ha fijado app.tenant_id,
current_setting('app.tenant_id', true) devuelve '' (cadena vacía), y ''::uuid
lanza error. Con NULLIF(..., '') el vacío se convierte en NULL -> no se ve
ninguna fila (y los INSERT quedan bloqueados), que es justo lo que queremos.

Revision ID: 0002_rls_nullif
Revises: 0001_nutrition
Create Date: 2026-09-23
"""
from __future__ import annotations

from alembic import op

revision = "0002_rls_nullif"
down_revision = "0001_nutrition"
branch_labels = None
depends_on = None

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


def upgrade() -> None:
    for table in TENANT_TABLES:
        op.execute(f"DROP POLICY IF EXISTS tenant_isolation ON {table}")
        op.execute(
            f"CREATE POLICY tenant_isolation ON {table} "
            f"USING (tenant_id = NULLIF(current_setting('app.tenant_id', true), '')::uuid) "
            f"WITH CHECK (tenant_id = NULLIF(current_setting('app.tenant_id', true), '')::uuid)"
        )


def downgrade() -> None:
    for table in TENANT_TABLES:
        op.execute(f"DROP POLICY IF EXISTS tenant_isolation ON {table}")
        op.execute(
            f"CREATE POLICY tenant_isolation ON {table} "
            f"USING (tenant_id = current_setting('app.tenant_id', true)::uuid) "
            f"WITH CHECK (tenant_id = current_setting('app.tenant_id', true)::uuid)"
        )