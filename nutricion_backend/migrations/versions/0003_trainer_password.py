"""Añade password_hash a trainer (para login).

Revision ID: 0003_trainer_password
Revises: 0002_rls_nullif
Create Date: 2026-09-23
"""
from __future__ import annotations

import sqlalchemy as sa
from alembic import op

revision = "0003_trainer_password"
down_revision = "0002_rls_nullif"
branch_labels = None
depends_on = None


def upgrade() -> None:
    # server_default="" para no romper filas ya existentes; luego se quita el
    # default para que las nuevas filas deban traer el hash desde la app.
    op.add_column(
        "trainer",
        sa.Column("password_hash", sa.String(255), nullable=False, server_default=""),
    )
    op.alter_column("trainer", "password_hash", server_default=None)


def downgrade() -> None:
    op.drop_column("trainer", "password_hash")
