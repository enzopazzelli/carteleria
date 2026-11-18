"""pasos del ajuste

Revision ID: a7d3e9c2b564
Revises: 9d3b6a1c7e45
Create Date: 2026-11-18 20:00:00.000000

A27: lo que se puede deshacer del ajuste del anidado (mover, girar, pasar de
chapa). Cada paso guarda la foto del anidado de antes del cambio. Se borran
junto con su anidado.
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = 'a7d3e9c2b564'
down_revision: Union[str, Sequence[str], None] = '9d3b6a1c7e45'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        'pasos_del_ajuste',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('ejecucion_id', sa.Integer(), nullable=False),
        sa.Column('tipo', sa.String(length=20), nullable=False),
        sa.Column('pieza', sa.String(length=40), nullable=False),
        sa.Column('descripcion', sa.String(length=200), nullable=False),
        sa.Column('foto', sa.JSON(), nullable=False),
        sa.Column('creado_en', sa.DateTime(timezone=True), nullable=False),
        sa.Column('actualizado_en', sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(['ejecucion_id'], ['ejecuciones_nesting.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id'),
    )
    op.create_index('ix_pasos_del_ajuste_ejecucion_id', 'pasos_del_ajuste', ['ejecucion_id'])


def downgrade() -> None:
    op.drop_index('ix_pasos_del_ajuste_ejecucion_id', table_name='pasos_del_ajuste')
    op.drop_table('pasos_del_ajuste')
