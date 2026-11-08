"""el historial de estados del presupuesto

Revision ID: b5d7a9c3e142
Revises: a3c9f1e2b7d4
Create Date: 2026-11-08 12:00:00.000000

A20: la tabla donde queda cada cambio de estado de un presupuesto (de cuál a
cuál, quién y por qué). Los presupuestos que ya había siguen en borrador y
arrancan con el historial vacío.
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = 'b5d7a9c3e142'
down_revision: Union[str, Sequence[str], None] = 'a3c9f1e2b7d4'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        'cambios_de_estado',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('presupuesto_id', sa.Integer(), nullable=False),
        sa.Column('estado_anterior', sa.String(length=20), nullable=False),
        sa.Column('estado_nuevo', sa.String(length=20), nullable=False),
        sa.Column('por', sa.String(length=120), nullable=False),
        sa.Column('motivo', sa.Text(), nullable=True),
        sa.Column('creado_en', sa.DateTime(timezone=True), nullable=False),
        sa.Column('actualizado_en', sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(['presupuesto_id'], ['presupuestos.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id'),
    )


def downgrade() -> None:
    op.drop_table('cambios_de_estado')
